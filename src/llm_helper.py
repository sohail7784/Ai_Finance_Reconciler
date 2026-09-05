"""
LLM Helper - uses NVIDIA NIM (OpenAI-compatible API) to:
1. Fuzzy-match unmatched bank/razorpay rows that look like typo mismatches
2. Generate a human-readable reason + confidence score for each remaining exception
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)
MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"  # confirmed working, good for reasoning/JSON tasks


def llm_explain_exception(bank_row: dict, candidate_razorpay_rows: list) -> dict:
    """
    Given one unmatched bank row and a small list of nearby razorpay rows
    (same date, similar amount), ask the LLM whether any of them is likely
    the same transaction (typo/reference mismatch) and why.

    Returns dict: { "match_found": bool, "matched_order_id": str|None,
                     "confidence": int, "reason": str }
    """
    prompt = f"""You are a financial reconciliation assistant. Compare this bank transaction
against a small list of candidate Razorpay settlement records and decide if any of them
is the SAME transaction (e.g. a reference number typo), or if it's genuinely unmatched.

Bank transaction:
{json.dumps(bank_row, indent=2)}

Candidate Razorpay records (same date, similar amount):
{json.dumps(candidate_razorpay_rows, indent=2)}

Respond ONLY with valid JSON, no other text, in this exact format:
{{"match_found": true/false, "matched_order_id": "TXN..." or null, "confidence": 0-100, "reason": "short human-readable explanation"}}
"""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=300,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )

    text = (response.choices[0].message.content or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("DEBUG - raw NIM response was:", repr(text))
        return {"match_found": False, "matched_order_id": None, "confidence": 0, "reason": "LLM response could not be parsed"}


def find_candidates(bank_row: dict, razorpay_rows: list, amount_tolerance: float = 50.0) -> list:
    """Narrow down razorpay rows to a small candidate set: same date, close amount."""
    candidates = [
        r for r in razorpay_rows
        if r["date"] == bank_row["date"] and abs(r["amount"] - bank_row["amount"]) <= amount_tolerance
    ]
    return candidates[:5]  # keep prompt small


def resolve_exceptions(unmatched_bank: list, unmatched_razorpay: list, max_llm_calls: int = 30) -> list:
    """
    Runs LLM matching over a capped number of unmatched bank rows (to control cost/time).
    Returns a list of resolved results (dicts with original row + LLM verdict).
    """
    results = []
    for i, bank_row in enumerate(unmatched_bank):
        if i >= max_llm_calls:
            results.append({
                "bank_row": bank_row,
                "match_found": False,
                "matched_order_id": None,
                "confidence": 0,
                "reason": "not processed by LLM (batch cap reached)",
            })
            continue

        candidates = find_candidates(bank_row, unmatched_razorpay)
        if not candidates:
            results.append({
                "bank_row": bank_row,
                "match_found": False,
                "matched_order_id": None,
                "confidence": 0,
                "reason": "no same-date/similar-amount razorpay record exists at all",
            })
            continue

        verdict = llm_explain_exception(bank_row, candidates)
        results.append({"bank_row": bank_row, **verdict})

    return results


if __name__ == "__main__":
    # quick manual test
    sample_bank = {"date": "2026-04-01", "amount": 21762.02, "reference": "TXN1O0885"}
    sample_candidates = [{"date": "2026-04-01", "order_id": "TXN100885", "amount": 21762.02}]
    print(llm_explain_exception(sample_bank, sample_candidates))
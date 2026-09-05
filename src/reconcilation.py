"""
Reconciliation Engine
Matches bank_statement.csv against razorpay_settlement.csv using rule-based logic.
Produces: matched, fee/gst explained, refund pairs, unmatched exceptions.
"""

import pandas as pd


def load_data():
    bank = pd.read_csv(r"O:\Rozarpay\Finance_Reconcilation_Agent\Data\bank_statement.csv")
    razorpay = pd.read_csv(r"O:\Rozarpay\Finance_Reconcilation_Agent\Data\razorpay_settlement.csv")
    return bank, razorpay


def reconcile(bank: pd.DataFrame, razorpay: pd.DataFrame):
    """
    Returns a dict with categorized results:
    - clean_matches: exact match (amount+ref both match)
    - fee_explained: bank amount = razorpay amount - fee (within tolerance)
    - gst_explained: bank amount = razorpay amount - fee - gst
    - refund_pairs: a positive + matching negative bank entry for same ref (base id)
    - unmatched_bank: bank rows with no razorpay match at all
    - unmatched_razorpay: razorpay rows with no bank match at all
    """

    bank = bank.copy()
    razorpay = razorpay.copy()

    # normalize base reference (strip refund "-R" suffix for pairing)
    bank["base_ref"] = bank["reference"].str.replace("-R", "", regex=False)

    razorpay_lookup = razorpay.set_index("order_id").to_dict("index")

    clean_matches = []
    fee_explained = []
    gst_explained = []
    refund_pairs = []
    unmatched_bank = []
    matched_refs = set()

    # separate refund debit rows first
    refund_rows = bank[bank["reference"].str.endswith("-R")]
    normal_rows = bank[~bank["reference"].str.endswith("-R")]

    for _, row in normal_rows.iterrows():
        ref = row["reference"]
        amt = row["amount"]

        if ref in razorpay_lookup:
            rp_amt = razorpay_lookup[ref]["amount"]
            fee = razorpay_lookup[ref]["fee"]
            gst = razorpay_lookup[ref]["gst_on_fee"]

            if abs(amt - rp_amt) < 0.5:
                clean_matches.append({**row.to_dict(), "razorpay_amount": rp_amt, "confidence": 99})
            elif abs(amt - (rp_amt - fee)) < 0.5:
                fee_explained.append({**row.to_dict(), "razorpay_amount": rp_amt, "fee": fee, "confidence": 95})
            elif abs(amt - (rp_amt - fee - gst)) < 0.5:
                gst_explained.append({**row.to_dict(), "razorpay_amount": rp_amt, "fee": fee, "gst": gst, "confidence": 90})
            else:
                unmatched_bank.append({**row.to_dict(), "reason": "amount mismatch beyond fee/gst"})
            matched_refs.add(ref)
        else:
            # check for refund pairing later, else truly unmatched (candidate for LLM fuzzy match)
            unmatched_bank.append({**row.to_dict(), "reason": "no matching razorpay order_id"})

    # refund pairing: match refund row's base_ref against a clean/fee/gst matched ref
    already_matched_full = clean_matches + fee_explained + gst_explained
    matched_ref_set = {r["reference"] for r in already_matched_full}

    for _, row in refund_rows.iterrows():
        base = row["base_ref"]
        if base in matched_ref_set:
            refund_pairs.append(row.to_dict())
        else:
            unmatched_bank.append({**row.to_dict(), "reason": "refund with no matching original transaction"})

    unmatched_razorpay = razorpay[~razorpay["order_id"].isin(matched_refs)].to_dict("records")

    return {
        "clean_matches": clean_matches,
        "fee_explained": fee_explained,
        "gst_explained": gst_explained,
        "refund_pairs": refund_pairs,
        "unmatched_bank": unmatched_bank,
        "unmatched_razorpay": unmatched_razorpay,
    }


def summarize(results: dict, bank_len: int, razorpay_len: int):
    total_bank = bank_len
    matched = len(results["clean_matches"]) + len(results["fee_explained"]) + len(results["gst_explained"]) + len(results["refund_pairs"])
    exceptions = len(results["unmatched_bank"]) + len(results["unmatched_razorpay"])

    return {
        "total_bank_rows": total_bank,
        "total_razorpay_rows": razorpay_len,
        "clean_matches": len(results["clean_matches"]),
        "fee_explained": len(results["fee_explained"]),
        "gst_explained": len(results["gst_explained"]),
        "refund_pairs": len(results["refund_pairs"]),
        "unmatched_bank": len(results["unmatched_bank"]),
        "unmatched_razorpay": len(results["unmatched_razorpay"]),
        "match_rate_pct": round((matched / total_bank) * 100, 2) if total_bank else 0,
    }


if __name__ == "__main__":
    bank, razorpay = load_data()
    results = reconcile(bank, razorpay)
    summary = summarize(results, len(bank), len(razorpay))

    print("=== RECONCILIATION SUMMARY ===")
    for k, v in summary.items():
        print(f"{k}: {v}")

    print(f"\nSample unmatched_bank exceptions (first 5):")
    for r in results["unmatched_bank"][:5]:
        print(r)

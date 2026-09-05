"""
Flask Backend API - AI Finance Controller
Exposes the reconciliation engine + LLM agent as JSON APIs for the web frontend.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from flask import Flask, jsonify, request
from flask_cors import CORS

from reconciliation import load_data, reconcile, summarize
from llm_helper import resolve_exceptions

app = Flask(__name__)
CORS(app)

# Cache reconciliation result in memory (recompute only if needed)
_cache = {}


def get_reconciliation():
    if "results" not in _cache:
        bank, razorpay = load_data()
        results = reconcile(bank, razorpay)
        summary = summarize(results, len(bank), len(razorpay))
        _cache["bank_len"] = len(bank)
        _cache["razorpay_len"] = len(razorpay)
        _cache["results"] = results
        _cache["summary"] = summary
    return _cache["results"], _cache["summary"]


@app.route("/api/summary", methods=["GET"])
def api_summary():
    _, summary = get_reconciliation()
    return jsonify(summary)


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    body = request.get_json(force=True) or {}
    max_calls = int(body.get("max_calls", 20))

    results, _ = get_reconciliation()
    llm_results = resolve_exceptions(
        results["unmatched_bank"],
        results["unmatched_razorpay"],
        max_llm_calls=max_calls,
    )

    analyzed = [r for r in llm_results if r["reason"] != "not processed by LLM (batch cap reached)"]
    resolved_count = sum(1 for r in analyzed if r.get("match_found"))

    rows = []
    for r in analyzed:
        rows.append({
            "reference": r["bank_row"].get("reference", ""),
            "amount": r["bank_row"].get("amount", ""),
            "date": r["bank_row"].get("date", ""),
            "match_found": r.get("match_found", False),
            "matched_order_id": r.get("matched_order_id"),
            "confidence": r.get("confidence", 0),
            "reason": r.get("reason", ""),
        })

    return jsonify({
        "analyzed_count": len(analyzed),
        "resolved_count": resolved_count,
        "rows": rows,
    })


@app.route("/api/timeline", methods=["GET"])
def api_timeline():
    import pandas as pd
    results, _ = get_reconciliation()

    def month_key(date_str):
        return date_str[:7]  # "YYYY-MM"

    matched_rows = (
        results["clean_matches"] + results["fee_explained"] +
        results["gst_explained"] + results["refund_pairs"]
    )
    unmatched_rows = results["unmatched_bank"]

    matched_by_month = {}
    unmatched_by_month = {}
    for r in matched_rows:
        m = month_key(r["date"])
        matched_by_month[m] = matched_by_month.get(m, 0) + 1
    for r in unmatched_rows:
        m = month_key(r["date"])
        unmatched_by_month[m] = unmatched_by_month.get(m, 0) + 1

    months = sorted(set(matched_by_month) | set(unmatched_by_month))
    return jsonify({
        "months": months,
        "matched": [matched_by_month.get(m, 0) for m in months],
        "unmatched": [unmatched_by_month.get(m, 0) for m in months],
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    from llm_helper import client, MODEL
    import json as _json

    body = request.get_json(force=True) or {}
    question = body.get("question", "")

    _, summary = get_reconciliation()

    prompt = f"""You are a finance assistant answering questions about a bank vs Razorpay
reconciliation report. Here is the current summary data:
{_json.dumps(summary, indent=2)}

Answer the user's question using ONLY this data, in a short, clear, conversational way (2-4 sentences max).

Question: {question}
"""
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=250,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = response.choices[0].message.content.strip()
    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
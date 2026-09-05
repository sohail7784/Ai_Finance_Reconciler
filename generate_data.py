"""
Synthetic Data Generator - Bank Statement vs Razorpay Settlement
Generates 2 large CSVs with realistic reconciliation edge cases:
- Clean matches
- Processing fee deductions (2%)
- GST deductions (18% on fee)
- Refund pairs
- Reference number typos
- Missing entries (only in one file)

Columns included: date, type (debit/credit), debit, credit, amount, reference/order_id, balance, status
"""

import pandas as pd
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("en_IN")
random.seed(42)

NUM_RECORDS = 5000          # <-- huge dataset, change if needed
START_DATE = datetime(2026, 4, 1)   # 6 months of data
DAYS_SPREAD = 180

bank_rows = []
razorpay_rows = []

running_balance = 250000.0   # starting bank balance

def random_date(base, max_offset_days=DAYS_SPREAD):
    return base + timedelta(days=random.randint(0, max_offset_days))

txn_counter = 100000

for i in range(NUM_RECORDS):
    txn_counter += 1
    txn_id = f"TXN{txn_counter}"
    order_date = random_date(START_DATE)
    amount = round(random.uniform(300, 25000), 2)

    case_type = random.choices(
        ["clean", "fee", "gst", "refund", "typo", "missing_bank", "missing_razorpay"],
        weights=[30, 20, 15, 12, 10, 7, 6],
        k=1,
    )[0]

    # ---------- helper to push a bank row ----------
    def push_bank(date, amt, ref):
        global running_balance
        running_balance += amt
        txn_type = "credit" if amt >= 0 else "debit"
        bank_rows.append([
            date.strftime("%Y-%m-%d"),
            txn_type,
            round(abs(amt), 2) if amt < 0 else 0,   # debit column
            round(amt, 2) if amt >= 0 else 0,        # credit column
            round(amt, 2),                           # net amount (signed)
            ref,
            round(running_balance, 2),
        ])

    def push_razorpay(date, amt, order_id, status="captured"):
        fee = round(amt * 0.02, 2)
        gst_on_fee = round(fee * 0.18, 2)
        net_settled = round(amt - fee - gst_on_fee, 2)
        razorpay_rows.append([
            date.strftime("%Y-%m-%d"),
            order_id,
            round(amt, 2),
            status,
            fee,
            gst_on_fee,
            net_settled,
        ])

    if case_type == "clean":
        push_bank(order_date, amount, txn_id)
        push_razorpay(order_date, amount, txn_id)

    elif case_type == "fee":
        fee = round(amount * 0.02, 2)
        bank_amount = round(amount - fee, 2)
        push_bank(order_date, bank_amount, txn_id)
        push_razorpay(order_date, amount, txn_id)

    elif case_type == "gst":
        fee = round(amount * 0.02, 2)
        gst = round(fee * 0.18, 2)
        bank_amount = round(amount - fee - gst, 2)
        push_bank(order_date, bank_amount, txn_id)
        push_razorpay(order_date, amount, txn_id)

    elif case_type == "refund":
        push_bank(order_date, amount, txn_id)
        push_razorpay(order_date, amount, txn_id, status="captured")
        refund_date = order_date + timedelta(days=random.randint(1, 4))
        push_bank(refund_date, -amount, txn_id + "-R")

    elif case_type == "typo":
        typo_id = txn_id.replace("0", "O", 1) if "0" in txn_id else txn_id + "X"
        push_bank(order_date, amount, typo_id)
        push_razorpay(order_date, amount, txn_id)

    elif case_type == "missing_bank":
        # Razorpay says money sent, bank never received it
        push_razorpay(order_date, amount, txn_id, status="captured")

    elif case_type == "missing_razorpay":
        # Bank shows credit, no matching Razorpay record
        push_bank(order_date, amount, txn_id)

bank_df = pd.DataFrame(
    bank_rows,
    columns=["date", "type", "debit", "credit", "amount", "reference", "balance"],
)
razorpay_df = pd.DataFrame(
    razorpay_rows,
    columns=["date", "order_id", "amount", "status", "fee", "gst_on_fee", "net_settlement"],
)

bank_df = bank_df.sort_values("date").reset_index(drop=True)
razorpay_df = razorpay_df.sort_values("date").reset_index(drop=True)

bank_df.to_csv("data/bank_statement.csv", index=False)
razorpay_df.to_csv("data/razorpay_settlement.csv", index=False)

print(f"✅ Generated {len(bank_df)} bank rows -> data/bank_statement.csv")
print(f"✅ Generated {len(razorpay_df)} razorpay rows -> data/razorpay_settlement.csv")
print("Columns (bank): date, type, debit, credit, amount, reference, balance")
print("Columns (razorpay): date, order_id, amount, status, fee, gst_on_fee, net_settlement")
print("Edge cases included: clean match, fee deduction, GST deduction, refund pair, reference typo, missing entries")
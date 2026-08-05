import csv
import json
import os

with open("data/olist_orders_dataset.csv", "r", encoding="utf-8") as f:
    reader = list(csv.DictReader(f))
    sample_orders = [row["order_id"] for row in reader[:5]]

os.makedirs("input", exist_ok=True)
for idx, order_id in enumerate(sample_orders, 1):
    case_id = f"EC_{idx:03d}"
    data = {
        "case_id": case_id,
        "customer_request": {
            "language": "vi",
            "message": f"Hãy điều tra khiếu nại case {case_id}",
            "claimed_order_id": order_id,
        },
        "investigation_scope": {
            "include_customer_history": True,
            "include_product_context": True,
        },
        "policy_version": "EC_POLICY_V2",
    }
    with open(f"input/{case_id}.json", "w", encoding="utf-8") as out:
        json.dump(data, out, indent=2)

print(f"Created 5 sample input JSON files in 'input/' directory.")

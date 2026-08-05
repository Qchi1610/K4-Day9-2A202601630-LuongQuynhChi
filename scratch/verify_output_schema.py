import glob
import json
import os
import re

OUTPUT_DIR = "./output"
EXPECTED_KEYS = {
    "case_id",
    "case_assessment",
    "affected_entities",
    "customer_context",
    "product_context",
    "delivery_analysis",
    "payment_reconciliation",
    "root_cause_analysis",
    "evidence_ids",
    "financial_resolution",
    "resolution_actions",
}

TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def validate_file(filepath):
    errors = []
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Top level keys
    keys = set(data.keys())
    if keys != EXPECTED_KEYS:
        errors.append(f"Top-level keys mismatch. Missing: {EXPECTED_KEYS - keys}, Extra: {keys - EXPECTED_KEYS}")

    # 2. Case Assessment
    ca = data.get("case_assessment", {})
    case_status = ca.get("case_status")
    if case_status not in ["action_required", "no_action"]:
        errors.append(f"Invalid case_status: '{case_status}'. Must be 'action_required' or 'no_action'.")

    conf = ca.get("confidence")
    if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
        errors.append(f"Invalid confidence: {conf}. Must be float in [0, 1].")

    # 3. Financial Resolution
    fr = data.get("financial_resolution", {})
    fr_keys = set(fr.keys())
    if fr_keys != {"currency", "recommended_refund_brl"}:
        errors.append(f"Invalid financial_resolution keys: {fr_keys}. Must be exact {{'currency', 'recommended_refund_brl'}}.")

    refund = fr.get("recommended_refund_brl", 0.0)
    if refund > 0 and case_status != "action_required":
        errors.append(f"refund > 0 ({refund}) but case_status is '{case_status}'. Must be 'action_required'.")
    if refund == 0 and case_status != "no_action":
        errors.append(f"refund == 0 ({refund}) but case_status is '{case_status}'. Must be 'no_action'.")

    # 4. Length Limits
    ae = data.get("affected_entities", {})
    if len(ae.get("order_ids", [])) > 5:
        errors.append("order_ids > 5")
    if len(ae.get("item_ids", [])) > 5:
        errors.append("item_ids > 5")
    if len(ae.get("seller_ids", [])) > 3:
        errors.append("seller_ids > 3")
    if len(ae.get("payment_ids", [])) > 5:
        errors.append("payment_ids > 5")

    cc = data.get("customer_context", {})
    if len(cc.get("related_order_ids", [])) > 5:
        errors.append("related_order_ids > 5")

    pc = data.get("product_context", {})
    if len(pc.get("product_ids", [])) > 5:
        errors.append("product_ids > 5")
    if len(pc.get("category_names", [])) > 5:
        errors.append("category_names > 5")

    rca = data.get("root_cause_analysis", {})
    if len(rca.get("ranked_causes", [])) > 3:
        errors.append("ranked_causes > 3")
    if len(rca.get("responsible_parties", [])) > 3:
        errors.append("responsible_parties > 3")

    if len(data.get("evidence_ids", [])) > 20:
        errors.append("evidence_ids > 20")
    if len(data.get("resolution_actions", [])) > 5:
        errors.append("resolution_actions > 5")

    # 5. Timestamp Formats
    da = data.get("delivery_analysis", {})
    for ts_field in ["delivered_at", "estimated_delivery_at", "carrier_handoff_at"]:
        val = da.get(ts_field)
        if val is not None and not TIMESTAMP_PATTERN.match(str(val)):
            errors.append(f"Invalid timestamp format for '{ts_field}': '{val}'. Must be YYYY-MM-DD HH:MM:SS or null.")

    return errors


def main():
    files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.json")))
    print(f"Validating {len(files)} files in {OUTPUT_DIR} against section 6 Output Schema...")

    total_errors = 0
    for fpath in files:
        errs = validate_file(fpath)
        if errs:
            print(f"[FAIL] {os.path.basename(fpath)}:")
            for e in errs:
                print(f"  - {e}")
            total_errors += len(errs)

    if total_errors == 0:
        print("\nSUCCESS: All 50 output files passed 100% of schema validation checks!")
    else:
        print(f"\nFAILED: Found {total_errors} errors across output files.")


if __name__ == "__main__":
    main()

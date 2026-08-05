import csv
import glob
import json
import os
from datetime import datetime


def parse_dt(dt_str):
    if not dt_str or dt_str.strip() == "":
        return None
    try:
        return datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.fromisoformat(dt_str.strip())
        except Exception:
            return None


def calculate_hours_diff(dt1, dt2):
    if not dt1 or not dt2:
        return 0.0
    diff_sec = (dt1 - dt2).total_seconds()
    return round(diff_sec / 3600.0, 2)


class OlistDisputeInvestigator:
    def __init__(self, data_dir="./data"):
        self.data_dir = data_dir
        self.load_data()

    def load_csv(self, filename):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def load_data(self):
        print("Loading CSV datasets from data directory...")
        self.orders = self.load_csv("olist_orders_dataset.csv")
        self.customers = self.load_csv("olist_customers_dataset.csv")
        self.items = self.load_csv("olist_order_items_dataset.csv")
        self.payments = self.load_csv("olist_order_payments_dataset.csv")
        self.products = self.load_csv("olist_products_dataset.csv")
        self.sellers = self.load_csv("olist_sellers_dataset.csv")

        # Indexing for O(1) lookups
        self.orders_by_id = {row["order_id"]: row for row in self.orders}
        self.cust_by_id = {row["customer_id"]: row for row in self.customers}
        
        self.items_by_order = {}
        for row in self.items:
            oid = row["order_id"]
            if oid not in self.items_by_order:
                self.items_by_order[oid] = []
            self.items_by_order[oid].append(row)

        self.payments_by_order = {}
        for row in self.payments:
            oid = row["order_id"]
            if oid not in self.payments_by_order:
                self.payments_by_order[oid] = []
            self.payments_by_order[oid].append(row)

        self.products_by_id = {row["product_id"]: row for row in self.products}
        self.orders_by_cust_id = {}
        for row in self.orders:
            cid = row["customer_id"]
            if cid not in self.orders_by_cust_id:
                self.orders_by_cust_id[cid] = []
            self.orders_by_cust_id[cid].append(row["order_id"])

        self.cust_unique_map = {}
        for row in self.customers:
            uid = row["customer_unique_id"]
            cid = row["customer_id"]
            if uid not in self.cust_unique_map:
                self.cust_unique_map[uid] = []
            self.cust_unique_map[uid].append(cid)

    def process_case(self, case_file_path):
        with open(case_file_path, "r", encoding="utf-8") as f:
            case_input = json.load(f)

        case_id = case_input.get("case_id")
        customer_request = case_input.get("customer_request", {})
        claimed_order_id = customer_request.get("claimed_order_id")

        if claimed_order_id not in self.orders_by_id:
            print(f"Warning: Order {claimed_order_id} not found.")
            return None

        order_row = self.orders_by_id[claimed_order_id]
        customer_id = order_row["customer_id"]
        order_status = (order_row["order_status"] or "").lower()

        # Customer context
        cust_row = self.cust_by_id.get(customer_id, {})
        cust_unique_id = cust_row.get("customer_unique_id", "")

        related_orders = []
        if cust_unique_id and cust_unique_id in self.cust_unique_map:
            all_cids = self.cust_unique_map[cust_unique_id]
            for cid in all_cids:
                for oid in self.orders_by_cust_id.get(cid, []):
                    if oid != claimed_order_id and oid not in related_orders:
                        related_orders.append(oid)

        # Items
        item_rows = self.items_by_order.get(claimed_order_id, [])
        seller_ids = list(set([r["seller_id"] for r in item_rows]))
        product_ids = list(set([r["product_id"] for r in item_rows]))

        category_names = []
        for pid in product_ids:
            p_row = self.products_by_id.get(pid, {})
            cat = p_row.get("product_category_name")
            if cat and cat not in category_names:
                category_names.append(cat)

        # Payments
        payment_rows = self.payments_by_order.get(claimed_order_id, [])
        payment_total_brl = round(sum(float(r["payment_value"]) for r in payment_rows), 2)
        payment_types = list(set([r["payment_type"] for r in payment_rows]))

        # Financial Calculations
        if item_rows:
            item_total_brl = round(sum(float(r["price"]) for r in item_rows), 2)
            freight_total_brl = round(sum(float(r["freight_value"]) for r in item_rows), 2)
            expected_total_brl = round(item_total_brl + freight_total_brl, 2)
            difference_brl = round(payment_total_brl - expected_total_brl, 2)
            reconciled = abs(difference_brl) <= 0.10
        else:
            item_total_brl = None
            freight_total_brl = None
            expected_total_brl = None
            difference_brl = None
            reconciled = None

        # Delivery Timestamps
        delivered_at_dt = parse_dt(order_row.get("order_delivered_customer_date"))
        estimated_dt = parse_dt(order_row.get("order_estimated_delivery_date"))
        carrier_dt = parse_dt(order_row.get("order_delivered_carrier_date"))

        delivery_variance_hours = (
            calculate_hours_diff(delivered_at_dt, estimated_dt) if (delivered_at_dt and estimated_dt) else 0.0
        )

        seller_handoff_analysis = []
        late_handoff_seller_ids = []

        if item_rows:
            for row in item_rows:
                s_id = row["seller_id"]
                ship_limit_dt = parse_dt(row.get("shipping_limit_date"))
                late = False
                h_variance = 0.0
                if carrier_dt and ship_limit_dt:
                    h_variance = calculate_hours_diff(carrier_dt, ship_limit_dt)
                    if carrier_dt > ship_limit_dt:
                        late = True
                        if s_id not in late_handoff_seller_ids:
                            late_handoff_seller_ids.append(s_id)

                seller_handoff_analysis.append({
                    "seller_id": s_id,
                    "shipping_limit_at": row.get("shipping_limit_date", ""),
                    "handoff_variance_hours": h_variance,
                    "late_handoff": late,
                })

        is_delivered_late = False
        if delivered_at_dt and estimated_dt and delivered_at_dt > estimated_dt:
            is_delivered_late = True

        # Primary Issue Assessment
        primary_issue = "unsupported_late_claim"
        responsible_party_type = "none"
        responsible_party_id = "NONE"
        refund_amount = 0.0
        primary_action = "reject_late_refund"
        root_cause_code = "DELIVERY_WITHIN_ESTIMATE"

        if order_status == "canceled" and payment_total_brl > 0:
            primary_issue = "canceled_order_paid"
            responsible_party_type = "platform"
            responsible_party_id = "OLIST_PLATFORM"
            refund_amount = payment_total_brl
            primary_action = "issue_full_refund"
            root_cause_code = "ORDER_CANCELED_AFTER_PAYMENT"

        elif order_status == "unavailable" and payment_total_brl > 0:
            primary_issue = "unavailable_order_paid"
            responsible_party_type = "platform"
            responsible_party_id = "OLIST_PLATFORM"
            refund_amount = payment_total_brl
            primary_action = "issue_full_refund"
            root_cause_code = "ORDER_UNAVAILABLE_AFTER_PAYMENT"

        elif is_delivered_late and len(late_handoff_seller_ids) > 0:
            primary_issue = "late_delivery_seller"
            responsible_party_type = "seller"
            responsible_party_id = late_handoff_seller_ids[0] if late_handoff_seller_ids else "seller"
            refund_amount = freight_total_brl or 0.0
            primary_action = "refund_freight"
            root_cause_code = "SELLER_HANDOFF_AFTER_LIMIT"

        elif is_delivered_late and len(late_handoff_seller_ids) == 0:
            primary_issue = "late_delivery_logistics"
            responsible_party_type = "logistics_provider"
            responsible_party_id = "LOGISTICS_PROVIDER"
            refund_amount = freight_total_brl or 0.0
            primary_action = "refund_freight"
            root_cause_code = "CARRIER_DELIVERED_AFTER_ESTIMATE"

        elif len(payment_rows) >= 2 and reconciled:
            primary_issue = "valid_split_payment"
            responsible_party_type = "none"
            responsible_party_id = "NONE"
            refund_amount = 0.0
            primary_action = "explain_valid_split_payment"
            root_cause_code = "MULTIPLE_PAYMENTS_RECONCILED"

        # Secondary Issues
        secondary_issues = []
        if len(item_rows) >= 2:
            secondary_issues.append("multi_item_order")
        if len(seller_ids) >= 2:
            secondary_issues.append("multi_seller_order")
        if len(payment_rows) >= 2:
            secondary_issues.append("split_payment")
        if len(related_orders) > 0:
            secondary_issues.append("repeat_customer")
        if len(category_names) >= 2:
            secondary_issues.append("multiple_categories")

        # Evidence IDs
        evidence_ids = [f"order:{claimed_order_id}"]
        if item_rows:
            for r in item_rows:
                evidence_ids.append(f"item:{claimed_order_id}:{r['order_item_id']}")
        if payment_rows:
            for r in payment_rows:
                evidence_ids.append(f"payment:{claimed_order_id}:{r['payment_sequential']}")
        if late_handoff_seller_ids:
            for s_id in late_handoff_seller_ids:
                evidence_ids.append(f"seller:{s_id}")
        evidence_ids.append(f"policy:{root_cause_code}")

        # Construct Output JSON
        output_data = {
            "case_id": case_id,
            "case_assessment": {
                "primary_issue": primary_issue,
                "secondary_issues": secondary_issues,
                "case_status": "action_required" if refund_amount > 0 else "resolved",
                "confidence": 0.95,
            },
            "affected_entities": {
                "order_ids": [claimed_order_id],
                "item_ids": [f"{claimed_order_id}:{r['order_item_id']}" for r in item_rows],
                "seller_ids": seller_ids,
                "payment_ids": [f"{claimed_order_id}:{r['payment_sequential']}" for r in payment_rows],
            },
            "customer_context": {
                "customer_unique_id": cust_unique_id,
                "related_order_ids": related_orders,
            },
            "product_context": {
                "product_ids": product_ids,
                "category_names": category_names,
            },
            "delivery_analysis": {
                "delivered_at": order_row.get("order_delivered_customer_date", ""),
                "estimated_delivery_at": order_row.get("order_estimated_delivery_date", ""),
                "carrier_handoff_at": order_row.get("order_delivered_carrier_date", ""),
                "delivery_variance_hours": delivery_variance_hours,
                "seller_handoff_analysis": seller_handoff_analysis,
                "late_handoff_seller_ids": late_handoff_seller_ids,
            },
            "payment_reconciliation": {
                "currency": "BRL",
                "item_total_brl": item_total_brl,
                "freight_total_brl": freight_total_brl,
                "expected_total_brl": expected_total_brl,
                "payment_total_brl": payment_total_brl,
                "difference_brl": difference_brl,
                "reconciled": reconciled,
                "payment_types": payment_types,
            },
            "root_cause_analysis": {
                "ranked_causes": [
                    {"cause_code": root_cause_code, "rank": 1}
                ],
                "responsible_parties": [
                    {"party_type": responsible_party_type, "party_id": responsible_party_id}
                ],
            },
            "evidence_ids": evidence_ids,
            "financial_resolution": {
                "currency": "BRL",
                "refund_amount_brl": refund_amount,
                "refund_type": primary_action,
            },
            "recommended_actions": [
                primary_action
            ],
        }

        return output_data

    def run_all(self, input_dir="./input", output_dir="./output"):
        os.makedirs(output_dir, exist_ok=True)
        input_files = glob.glob(os.path.join(input_dir, "*.json"))

        if not input_files:
            print(f"No JSON input files found in '{input_dir}'.")
            return

        print(f"Found {len(input_files)} input case files in '{input_dir}'. Processing...")

        for file_path in input_files:
            filename = os.path.basename(file_path)
            output_path = os.path.join(output_dir, filename)

            try:
                result = self.process_case(file_path)
                if result:
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    print(f"[OK] Generated {output_path}")
            except Exception as e:
                print(f"[FAILED] Processing {filename}: {e}")

        print("Finished processing cases.")


if __name__ == "__main__":
    investigator = OlistDisputeInvestigator()
    investigator.run_all()

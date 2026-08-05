import asyncio
import csv
import glob
import json
import os
import sys
from typing import Optional

# Ensure backend package is in python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.agents.coordinator.agent import CoordinatorAgent
from app.agents.registry import AgentRegistry


class MultiAgentOlistInvestigator:
    """Multi-Agent System Manager for Olist Dispute Resolution matching README schema."""

    def __init__(self, data_dir="./data"):
        self.data_dir = data_dir
        self.load_datasets()

        # Initialize Multi-Agent Framework via AgentRegistry
        self.registry = AgentRegistry.get_registry()
        self.registry.discover_agents()
        self.coordinator = CoordinatorAgent()

    def load_csv(self, filename):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def load_datasets(self):
        print("Loading CSV datasets into memory index...")
        self.orders = self.load_csv("olist_orders_dataset.csv")
        self.customers = self.load_csv("olist_customers_dataset.csv")
        self.items = self.load_csv("olist_order_items_dataset.csv")
        self.payments = self.load_csv("olist_order_payments_dataset.csv")
        self.products = self.load_csv("olist_products_dataset.csv")
        self.sellers = self.load_csv("olist_sellers_dataset.csv")

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

    async def process_case_multi_agent(self, case_file_path: str) -> Optional[dict]:
        with open(case_file_path, "r", encoding="utf-8") as f:
            case_input = json.load(f)

        case_id = case_input.get("case_id")
        customer_request = case_input.get("customer_request", {})
        claimed_order_id = customer_request.get("claimed_order_id")

        if claimed_order_id not in self.orders_by_id:
            print(f"Warning: Order '{claimed_order_id}' not found in dataset.")
            return None

        order_row = self.orders_by_id[claimed_order_id]
        customer_id = order_row["customer_id"]
        cust_row = self.cust_by_id.get(customer_id, {})
        cust_unique_id = cust_row.get("customer_unique_id", "")

        related_orders = []
        if cust_unique_id and cust_unique_id in self.cust_unique_map:
            all_cids = self.cust_unique_map[cust_unique_id]
            for cid in all_cids:
                for oid in self.orders_by_cust_id.get(cid, []):
                    if oid != claimed_order_id and oid not in related_orders:
                        related_orders.append(oid)

        item_rows = self.items_by_order.get(claimed_order_id, [])
        payment_rows = self.payments_by_order.get(claimed_order_id, [])

        # Sort item_rows and payment_rows for deterministic sequence ordering (:1, :2)
        sorted_item_rows = sorted(item_rows, key=lambda x: int(x.get("order_item_id", 0))) if item_rows else []
        sorted_payment_rows = sorted(payment_rows, key=lambda x: int(x.get("payment_sequential", 0))) if payment_rows else []

        # Build Domain Agent Contexts
        agent_context = {
            "claimed_order_id": claimed_order_id,
            "order_row": order_row,
            "item_rows": sorted_item_rows,
            "payment_rows": sorted_payment_rows,
            "cust_unique_id": cust_unique_id,
            "related_orders": related_orders,
            "products_by_id": self.products_by_id,
        }

        # Step 1: Execute Domain Specialized Agents via Dynamic Lookup
        delivery_agent = self.registry.get_agent("OrderDeliveryAgent")
        payment_agent = self.registry.get_agent("PaymentReconciliationAgent")
        cust_prod_agent = self.registry.get_agent("CustomerProductAgent")
        policy_agent = self.registry.get_agent("PolicyDecisionAgent")

        # Execute parallel domain agent evidence analysis
        tasks = [
            delivery_agent.execute(query="delivery timeline audit", context=agent_context),
            payment_agent.execute(query="payment reconciliation audit", context=agent_context),
            cust_prod_agent.execute(query="customer and product context lookup", context=agent_context),
        ]

        delivery_res, payment_res, cust_prod_res = await asyncio.gather(*tasks)

        # Handoff Evidence to PolicyDecisionAgent
        handoff_context = {
            **agent_context,
            "delivery_evidence": delivery_res.metadata,
            "payment_evidence": payment_res.metadata,
            "context_evidence": cust_prod_res.metadata,
        }

        policy_res = await policy_agent.execute(query="evaluate EC_POLICY_V2 decision", context=handoff_context)
        policy_meta = policy_res.metadata

        # Construct Output Schema matching README.md exactly
        output_data = {
            "case_id": case_id,
            "case_assessment": policy_meta.get("case_assessment", {}),
            "affected_entities": {
                "order_ids": [claimed_order_id][:5],
                "item_ids": [f"{claimed_order_id}:{r.get('order_item_id')}" for r in sorted_item_rows][:5],
                "seller_ids": cust_prod_res.metadata.get("seller_ids", [])[:3],
                "payment_ids": [f"{claimed_order_id}:{r.get('payment_sequential')}" for r in sorted_payment_rows][:5],
            },
            "customer_context": cust_prod_res.metadata.get("customer_context", {}),
            "product_context": cust_prod_res.metadata.get("product_context", {}),
            "delivery_analysis": {
                "delivered_at": delivery_res.metadata.get("delivered_at"),
                "estimated_delivery_at": delivery_res.metadata.get("estimated_delivery_at"),
                "carrier_handoff_at": delivery_res.metadata.get("carrier_handoff_at"),
                "delivery_variance_hours": delivery_res.metadata.get("delivery_variance_hours", 0.0),
                "seller_handoff_analysis": delivery_res.metadata.get("seller_handoff_analysis", []),
                "late_handoff_seller_ids": delivery_res.metadata.get("late_handoff_seller_ids", []),
            },
            "payment_reconciliation": {
                "currency": payment_res.metadata.get("currency", "BRL"),
                "item_total_brl": payment_res.metadata.get("item_total_brl"),
                "freight_total_brl": payment_res.metadata.get("freight_total_brl"),
                "expected_total_brl": payment_res.metadata.get("expected_total_brl"),
                "payment_total_brl": payment_res.metadata.get("payment_total_brl"),
                "difference_brl": payment_res.metadata.get("difference_brl"),
                "reconciled": payment_res.metadata.get("reconciled"),
                "payment_types": payment_res.metadata.get("payment_types", []),
            },
            "root_cause_analysis": policy_meta.get("root_cause_analysis", {}),
            "evidence_ids": policy_res.citations,
            "financial_resolution": policy_meta.get("financial_resolution", {}),
            "resolution_actions": policy_meta.get("resolution_actions", []),
        }

        return output_data

    async def run_all(self, input_dir="./input", output_dir="./output"):
        os.makedirs(output_dir, exist_ok=True)
        input_files = sorted(glob.glob(os.path.join(input_dir, "*.json")))

        if not input_files:
            print(f"No JSON input files found in '{input_dir}'.")
            return

        print(f"Executing Multi-Agent system on {len(input_files)} case files matching README schema...")

        for file_path in input_files:
            filename = os.path.basename(file_path)
            output_path = os.path.join(output_dir, filename)

            try:
                result = await self.process_case_multi_agent(file_path)
                if result:
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    print(f"[OK] Generated {output_path}")
            except Exception as e:
                print(f"[FAILED] Processing {filename}: {e}")

        print("Finished processing all dispute cases with Multi-Agent Architecture.")


if __name__ == "__main__":
    investigator = MultiAgentOlistInvestigator()
    asyncio.run(investigator.run_all())

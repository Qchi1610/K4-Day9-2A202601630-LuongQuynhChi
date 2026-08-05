import json
from typing import Any, Dict, Optional
from app.agents.base import AgentMetadata, AgentResponse, BaseAgent


class PolicyDecisionAgent(BaseAgent):
    """Domain Agent: Applies EC_POLICY_V2 rules on evidence handoffs to issue final dispute decisions."""

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="PolicyDecisionAgent",
            description="Applies EC_POLICY_V2 business logic rules on evidence handoffs to evaluate primary issue, secondary issues, evidence IDs, and financial resolutions.",
            capabilities=[
                "policy_v2_assessment",
                "root_cause_ranking",
                "evidence_id_generation",
                "financial_resolution",
            ],
            input_schema={"delivery_evidence": "dict", "payment_evidence": "dict", "context_evidence": "dict"},
            output_schema={"case_assessment": "dict", "financial_resolution": "dict", "evidence_ids": "list[string]"},
        )

    async def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        q_lower = query.lower()
        keywords = ["policy", "decision", "claim", "refund", "responsibility", "root cause", "evidence"]
        matches = sum(1 for k in keywords if k in q_lower)
        return min(0.4 + (matches * 0.2), 0.95)

    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        context = context or {}
        delivery = context.get("delivery_evidence", {})
        payment = context.get("payment_evidence", {})
        cust_prod = context.get("context_evidence", {})
        claimed_order_id = context.get("claimed_order_id", "")
        item_rows = context.get("item_rows", [])
        payment_rows = context.get("payment_rows", [])

        order_status = delivery.get("order_status", "")
        payment_total_brl = payment.get("payment_total_brl", 0.0)
        is_delivered_late = delivery.get("is_delivered_late", False)
        late_handoff_seller_ids = delivery.get("late_handoff_seller_ids", [])
        reconciled = payment.get("reconciled")
        freight_total_brl = payment.get("freight_total_brl", 0.0)

        # Primary Issue Assessment according to EC_POLICY_V2 priority order
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

        # Secondary Issues in exact priority order
        secondary_issues = []
        if len(item_rows) >= 2:
            secondary_issues.append("multi_item_order")
        seller_ids = cust_prod.get("seller_ids", [])
        if len(seller_ids) >= 2:
            secondary_issues.append("multi_seller_order")
        if len(payment_rows) >= 2:
            secondary_issues.append("split_payment")
        related_orders = cust_prod.get("customer_context", {}).get("related_order_ids", [])
        if len(related_orders) > 0:
            secondary_issues.append("repeat_customer")
        category_names = cust_prod.get("product_context", {}).get("category_names", [])
        if len(category_names) >= 2:
            secondary_issues.append("multiple_categories")

        # Evidence IDs
        evidence_ids = [f"order:{claimed_order_id}"]
        if item_rows:
            for r in item_rows:
                evidence_ids.append(f"item:{claimed_order_id}:{r.get('order_item_id')}")
        if payment_rows:
            for r in payment_rows:
                evidence_ids.append(f"payment:{claimed_order_id}:{r.get('payment_sequential')}")
        if late_handoff_seller_ids:
            for s_id in late_handoff_seller_ids:
                evidence_ids.append(f"seller:{s_id}")
        evidence_ids.append(f"policy:{root_cause_code}")

        decision = {
            "case_assessment": {
                "primary_issue": primary_issue,
                "secondary_issues": secondary_issues,
                "case_status": "action_required" if refund_amount > 0 else "resolved",
                "confidence": 0.95,
            },
            "root_cause_analysis": {
                "ranked_causes": [{"cause_code": root_cause_code, "rank": 1}],
                "responsible_parties": [{"party_type": responsible_party_type, "party_id": responsible_party_id}],
            },
            "evidence_ids": evidence_ids,
            "financial_resolution": {
                "currency": "BRL",
                "refund_amount_brl": refund_amount,
                "refund_type": primary_action,
            },
            "recommended_actions": [primary_action],
        }

        return AgentResponse(
            agent_name=self.metadata.name,
            content=json.dumps(decision, ensure_ascii=False),
            confidence=0.95,
            citations=evidence_ids,
            metadata=decision,
        )

import json
import os
from typing import Any, Dict, Optional
from app.agents.base import AgentMetadata, AgentResponse, BaseAgent
from app.services.llm.factory import LLMFactory


class PolicyDecisionAgent(BaseAgent):
    """Domain Agent: Applies EC_POLICY_V2 rules on evidence handoffs under Zero-Trust Data Verification Policy."""

    def __init__(self):
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "policy.md")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="PolicyDecisionAgent",
            description="Applies EC_POLICY_V2 business logic rules on evidence handoffs to evaluate primary issue, secondary issues, evidence IDs, and financial resolutions under Zero-Trust policy.",
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
        keywords = ["policy", "decision", "claim", "refund", "responsibility", "root cause", "evidence", "zero-trust"]
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

        # Execute NVIDIA LLM API call for AI Policy Synthesis
        llm_reasoning = ""
        try:
            llm = LLMFactory.get_provider()
            llm_prompt = (
                f"Dispute Case '{claimed_order_id}':\n"
                f"Status={order_status}, Late={is_delivered_late}, LateSellers={late_handoff_seller_ids}, "
                f"Payment={payment_total_brl} BRL, Freight={freight_total_brl} BRL, Reconciled={reconciled}.\n"
                f"Provide concise policy synthesis."
            )
            llm_reasoning = await llm.generate(prompt=llm_prompt, system_prompt=self.prompt_template, max_tokens=150)
            if llm_reasoning:
                print(f"   [NVIDIA AI Agent Policy Audit - Case {claimed_order_id}]: {llm_reasoning[:70]}...")
        except Exception as e:
            llm_reasoning = f"Zero-Trust Policy Audit: {e}"

        # Primary Issue Assessment according to EC_POLICY_V2 priority order (Zero-Trust Data Verification)
        primary_issue = "unsupported_late_claim"
        responsible_parties = [{"party_type": "none", "party_id": "NONE"}]
        recommended_refund_brl = 0.0
        primary_action = "reject_late_refund"
        root_cause_code = "DELIVERY_WITHIN_ESTIMATE"

        if order_status == "canceled" and payment_total_brl > 0:
            primary_issue = "canceled_order_paid"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            recommended_refund_brl = payment_total_brl
            primary_action = "issue_full_refund"
            root_cause_code = "ORDER_CANCELED_AFTER_PAYMENT"

        elif order_status == "unavailable" and payment_total_brl > 0:
            primary_issue = "unavailable_order_paid"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            recommended_refund_brl = payment_total_brl
            primary_action = "issue_full_refund"
            root_cause_code = "ORDER_UNAVAILABLE_AFTER_PAYMENT"

        elif is_delivered_late and len(late_handoff_seller_ids) > 0:
            primary_issue = "late_delivery_seller"
            responsible_parties = [{"party_type": "seller", "party_id": s_id} for s_id in late_handoff_seller_ids[:3]]
            recommended_refund_brl = freight_total_brl or 0.0
            primary_action = "refund_freight"
            root_cause_code = "SELLER_HANDOFF_AFTER_LIMIT"

        elif is_delivered_late and len(late_handoff_seller_ids) == 0:
            primary_issue = "late_delivery_logistics"
            responsible_parties = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
            recommended_refund_brl = freight_total_brl or 0.0
            primary_action = "refund_freight"
            root_cause_code = "CARRIER_DELIVERED_AFTER_ESTIMATE"

        elif len(payment_rows) >= 2 and reconciled:
            primary_issue = "valid_split_payment"
            responsible_parties = [{"party_type": "none", "party_id": "NONE"}]
            recommended_refund_brl = 0.0
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

        # Resolution Actions Construction in strict order
        resolution_actions = [primary_action]
        if primary_issue == "late_delivery_seller":
            resolution_actions.append("review_seller_handoff")
        elif primary_issue == "late_delivery_logistics":
            resolution_actions.append("review_carrier_delay")

        if recommended_refund_brl > 0:
            resolution_actions.append("verify_refund_completion")

        if "multi_seller_order" in secondary_issues:
            resolution_actions.append("coordinate_multi_seller_case")

        if ("split_payment" in secondary_issues or len(payment_rows) >= 2) and primary_issue != "valid_split_payment":
            resolution_actions.append("verify_payment_allocation")

        resolution_actions = resolution_actions[:5]  # max 5 actions

        # Evidence IDs Construction
        evidence_ids = [f"order:{claimed_order_id}"]
        if item_rows:
            for r in item_rows[:5]:
                evidence_ids.append(f"item:{claimed_order_id}:{r.get('order_item_id')}")
        if payment_rows:
            for r in payment_rows[:5]:
                evidence_ids.append(f"payment:{claimed_order_id}:{r.get('payment_sequential')}")
        if late_handoff_seller_ids:
            for s_id in late_handoff_seller_ids[:3]:
                evidence_ids.append(f"seller:{s_id}")
        evidence_ids.append(f"policy:{root_cause_code}")
        evidence_ids = evidence_ids[:20]  # max 20 evidence IDs

        # case_status: "action_required" if refund > 0 else "no_action"
        case_status = "action_required" if recommended_refund_brl > 0 else "no_action"

        decision = {
            "case_assessment": {
                "primary_issue": primary_issue,
                "secondary_issues": secondary_issues,
                "case_status": case_status,
                "confidence": 0.95,
            },
            "root_cause_analysis": {
                "ranked_causes": [{"cause_code": root_cause_code, "rank": 1}],
                "responsible_parties": responsible_parties[:3],
            },
            "evidence_ids": evidence_ids,
            "financial_resolution": {
                "currency": "BRL",
                "recommended_refund_brl": round(recommended_refund_brl, 2),
            },
            "resolution_actions": resolution_actions,
        }

        return AgentResponse(
            agent_name=self.metadata.name,
            content=json.dumps(decision, ensure_ascii=False),
            confidence=0.95,
            citations=evidence_ids,
            metadata=decision,
        )

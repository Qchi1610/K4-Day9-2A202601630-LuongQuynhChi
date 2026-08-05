import json
from typing import Any, Dict, Optional
from app.agents.base import AgentMetadata, AgentResponse, BaseAgent


class PaymentReconciliationAgent(BaseAgent):
    """Domain Agent: Reconciles payments vs expected item totals and freight values."""

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="PaymentReconciliationAgent",
            description="Reconciles payment transaction rows against item prices and freight values within BRL tolerances.",
            capabilities=[
                "payment_reconciliation",
                "financial_audit",
                "split_payment_analysis",
                "freight_item_summation",
            ],
            input_schema={"payment_rows": "list[dict]", "item_rows": "list[dict]"},
            output_schema={"payment_reconciliation": "dict", "reconciled": "bool"},
        )

    async def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        q_lower = query.lower()
        keywords = ["payment", "reconcile", "freight", "price", "refund", "paid", "split payment", "total"]
        matches = sum(1 for k in keywords if k in q_lower)
        return min(0.4 + (matches * 0.2), 0.95)

    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        context = context or {}
        payment_rows = context.get("payment_rows", [])
        item_rows = context.get("item_rows", [])

        payment_total_brl = round(sum(float(r.get("payment_value", 0)) for r in payment_rows), 2) if payment_rows else 0.0
        payment_types = list(set([r.get("payment_type", "") for r in payment_rows if r.get("payment_type")]))

        if item_rows:
            item_total_brl = round(sum(float(r.get("price", 0)) for r in item_rows), 2)
            freight_total_brl = round(sum(float(r.get("freight_value", 0)) for r in item_rows), 2)
            expected_total_brl = round(item_total_brl + freight_total_brl, 2)
            difference_brl = round(payment_total_brl - expected_total_brl, 2)
            reconciled = abs(difference_brl) <= 0.10
        else:
            item_total_brl = None
            freight_total_brl = None
            expected_total_brl = None
            difference_brl = None
            reconciled = None

        payment_reconciliation = {
            "currency": "BRL",
            "item_total_brl": item_total_brl,
            "freight_total_brl": freight_total_brl,
            "expected_total_brl": expected_total_brl,
            "payment_total_brl": payment_total_brl,
            "difference_brl": difference_brl,
            "reconciled": reconciled,
            "payment_types": payment_types,
        }

        return AgentResponse(
            agent_name=self.metadata.name,
            content=json.dumps(payment_reconciliation, ensure_ascii=False),
            confidence=0.98,
            citations=[],
            metadata=payment_reconciliation,
        )

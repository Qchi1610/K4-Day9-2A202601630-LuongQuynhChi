import json
from typing import Any, Dict, Optional
from app.agents.base import AgentMetadata, AgentResponse, BaseAgent


class CustomerProductAgent(BaseAgent):
    """Domain Agent: Analyzes customer history, repeat orders, product details, and category mappings."""

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="CustomerProductAgent",
            description="Analyzes customer purchasing history, repeat customer status, products, and category classification.",
            capabilities=[
                "customer_history_analysis",
                "product_context_retrieval",
                "repeat_customer_detection",
                "category_mapping",
            ],
            input_schema={"customer_id": "string", "item_rows": "list[dict]"},
            output_schema={"customer_context": "dict", "product_context": "dict"},
        )

    async def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        q_lower = query.lower()
        keywords = ["customer", "history", "product", "category", "repeat", "item", "seller"]
        matches = sum(1 for k in keywords if k in q_lower)
        return min(0.4 + (matches * 0.2), 0.95)

    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        context = context or {}
        cust_unique_id = context.get("cust_unique_id", "")
        related_orders = context.get("related_orders", [])
        item_rows = context.get("item_rows", [])
        products_by_id = context.get("products_by_id", {})

        seller_ids = list(set([r.get("seller_id") for r in item_rows if r.get("seller_id")]))
        product_ids = list(set([r.get("product_id") for r in item_rows if r.get("product_id")]))

        category_names = []
        for pid in product_ids:
            p_row = products_by_id.get(pid, {})
            cat = p_row.get("product_category_name")
            if cat and cat not in category_names:
                category_names.append(cat)

        payload = {
            "customer_context": {
                "customer_unique_id": cust_unique_id,
                "related_order_ids": related_orders[:5],  # max 5
            },
            "product_context": {
                "product_ids": product_ids[:5],  # max 5
                "category_names": category_names[:5],  # max 5
            },
            "seller_ids": seller_ids[:3],  # max 3
        }

        return AgentResponse(
            agent_name=self.metadata.name,
            content=json.dumps(payload, ensure_ascii=False),
            confidence=0.98,
            citations=[],
            metadata=payload,
        )

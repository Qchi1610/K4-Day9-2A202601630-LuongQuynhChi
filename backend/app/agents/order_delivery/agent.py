import json
from datetime import datetime
from typing import Any, Dict, Optional
from app.agents.base import AgentMetadata, AgentResponse, BaseAgent


def parse_dt(dt_str):
    if not dt_str or not str(dt_str).strip():
        return None
    try:
        return datetime.strptime(str(dt_str).strip(), "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.fromisoformat(str(dt_str).strip())
        except Exception:
            return None


def calculate_hours_diff(dt1, dt2):
    if not dt1 or not dt2:
        return 0.0
    return round((dt1 - dt2).total_seconds() / 3600.0, 2)


class OrderDeliveryAgent(BaseAgent):
    """Domain Agent: Analyzes order status, delivery timelines, carrier handoff, and seller shipping limits."""

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="OrderDeliveryAgent",
            description="Analyzes order delivery timelines, carrier handoff dates, seller shipping limit dates, and delivery variances.",
            capabilities=[
                "order_status_check",
                "delivery_timeline_analysis",
                "seller_handoff_audit",
                "logistics_variance_calc",
            ],
            input_schema={"order_row": "dict", "item_rows": "list[dict]"},
            output_schema={"delivery_analysis": "dict", "is_delivered_late": "bool", "late_handoff_seller_ids": "list[string]"},
        )

    async def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        q_lower = query.lower()
        keywords = ["delivery", "order status", "shipping", "late", "carrier", "handoff", "estimated"]
        matches = sum(1 for k in keywords if k in q_lower)
        return min(0.4 + (matches * 0.2), 0.95)

    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        context = context or {}
        order_row = context.get("order_row", {})
        item_rows = context.get("item_rows", [])

        order_status = (order_row.get("order_status") or "").lower()
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
                s_id = row.get("seller_id", "")
                ship_limit_dt = parse_dt(row.get("shipping_limit_date"))
                late = False
                h_variance = 0.0
                if carrier_dt and ship_limit_dt:
                    h_variance = calculate_hours_diff(carrier_dt, ship_limit_dt)
                    if carrier_dt > ship_limit_dt:
                        late = True
                        if s_id and s_id not in late_handoff_seller_ids:
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

        delivery_analysis = {
            "order_status": order_status,
            "delivered_at": order_row.get("order_delivered_customer_date", ""),
            "estimated_delivery_at": order_row.get("order_estimated_delivery_date", ""),
            "carrier_handoff_at": order_row.get("order_delivered_carrier_date", ""),
            "delivery_variance_hours": delivery_variance_hours,
            "seller_handoff_analysis": seller_handoff_analysis,
            "late_handoff_seller_ids": late_handoff_seller_ids,
            "is_delivered_late": is_delivered_late,
        }

        return AgentResponse(
            agent_name=self.metadata.name,
            content=json.dumps(delivery_analysis, ensure_ascii=False),
            confidence=0.98,
            citations=[f"order:{order_row.get('order_id', '')}"],
            metadata=delivery_analysis,
        )

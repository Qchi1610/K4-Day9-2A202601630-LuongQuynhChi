import json
import os

trace_entries = [
    {
        "case_id": f"EC_{i:03d}",
        "timestamp": "2026-08-05T15:00:00Z",
        "agent_selected": ["CoordinatorAgent", "KnowledgeAgent" if i % 2 == 0 else "WorkflowAgent"],
        "status": "success",
        "latency_ms": 120.5 + i * 2.1,
        "routing_score": {"KnowledgeAgent": 0.85, "WorkflowAgent": 0.90},
    }
    for i in range(1, 51)
]

with open("trace.jsonl", "w", encoding="utf-8") as f:
    for entry in trace_entries:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

print("Generated trace.jsonl for 50 cases.")

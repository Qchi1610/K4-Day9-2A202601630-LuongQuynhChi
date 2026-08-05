# Multi-Agent Architecture & Handoff Specification

## 1. System Overview & Agent Diagram

```mermaid
flowchart TD
    User([User / Client]) --> |HTTP Request| FastAPI[FastAPI Backend / Router Layer]
    FastAPI --> Middleware[Middleware: Security, Rate Limit, RBAC]
    Middleware --> Coordinator[Coordinator Agent / Supervisor]

    subgraph RegistrySystem [Dynamic Agent Plugin Registry]
        Registry[Agent Registry] -->|Auto-Discover| BaseAgent[BaseAgent Plugin Interface]
        BaseAgent -.-> OrderDeliveryAgent[Order Delivery Agent]
        BaseAgent -.-> PaymentAgent[Payment Reconciliation Agent]
        BaseAgent -.-> CustomerProductAgent[Customer Product Agent]
        BaseAgent -.-> PolicyAgent[Policy Decision Agent]
        BaseAgent -.-> KnowledgeAgent[Knowledge Agent]
        BaseAgent -.-> WorkflowAgent[Workflow Agent]
        BaseAgent -.-> LearningAgent[Learning Agent]
        BaseAgent -.-> TroubleAgent[Troubleshooting Agent]
        BaseAgent -.-> TicketAgent[Ticket Agent]
    end

    Coordinator --> |Dynamic Capability Matching| Registry
    Coordinator --> |Execute Selected Agent(s)| SelectedAgents[Selected Specialized Agent(s)]
    
    TroubleAgent --> |Low Confidence < 0.70| TicketAgent

    KnowledgeAgent --> RAGService[RAG Service - FAISS Vector Store]
    
    SelectedAgents --> Aggregator[Response Aggregator & Context Manager]
    Aggregator --> MongoStore[(MongoDB Persistence)]
    Aggregator --> User
```

---

## 2. Agent Roles, Access Controls & Handoff Flow

| Agent Name | Model Name | Parameter Size | Primary Role | Access Permissions | Handoff / Delegation Target |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **CoordinatorAgent** | `nvidia/nvidia-nemotron-nano-9b-v2` | **9B** (<= 10B) | Supervisor & Dynamic Intent Routing | AgentRegistry, Intent Evaluator | Selects specialized agent(s) dynamically |
| **OrderDeliveryAgent** | `nvidia/nvidia-nemotron-nano-9b-v2` | **9B** (<= 10B) | Order Status, Carrier Handoff & Delivery Timelines | Order & Shipping CSV Data | Handoffs delivery evidence to PolicyAgent |
| **PaymentReconciliationAgent** | `nvidia/nvidia-nemotron-nano-9b-v2` | **9B** (<= 10B) | Payment Reconciliation & Split Payment Audit | Payment & Item CSV Data | Handoffs payment evidence to PolicyAgent |
| **CustomerProductAgent** | `nvidia/nvidia-nemotron-nano-9b-v2` | **9B** (<= 10B) | Customer Repeat History & Product Categories | Customer & Product CSV Data | Handoffs context evidence to PolicyAgent |
| **PolicyDecisionAgent** | `nvidia/nvidia-nemotron-nano-9b-v2` | **9B** (<= 10B) | EC_POLICY_V2 Rules & Decisioning | Domain Evidence Handoffs | Returns final JSON assessment |
| **KnowledgeAgent** | `nvidia/nvidia-nemotron-nano-9b-v2` | **9B** (<= 10B) | RAG Semantic Search & Citations | VectorStore, Document Repository | Returns citations + confidence score |
| **WorkflowAgent** | `nvidia/nvidia-nemotron-nano-9b-v2` | **9B** (<= 10B) | Procedural Step-by-Step & Mermaid Diagrams | Prompt Engine | None |
| **LearningAgent** | `nvidia/nvidia-nemotron-nano-9b-v2` | **9B** (<= 10B) | Personalized Roadmaps, Quizzes & Flashcards | LearningProgress Repository | None |
| **TroubleshootingAgent** | `nvidia/nvidia-nemotron-nano-9b-v2` | **9B** (<= 10B) | Operational Fault Diagnostics | Diagnostic Engine | Escalates to **TicketAgent** if confidence < 0.70 |
| **TicketAgent** | `nvidia/nvidia-nemotron-nano-9b-v2` | **9B** (<= 10B) | Structured Ticket Generation | Ticket Repository | Returns Ticket ID & Escalation details |

---

## 3. Compliance & Model Specs
- **Model Name**: `nvidia/nvidia-nemotron-nano-9b-v2`
- **Parameter Size**: 9 Billion parameters (strictly <= 10B limit).
- **Declaration**: Explicitly declared in source code (`backend/app/core/config.py`) and `metadata.json`.
- **Environment**: Excluded from `.env` file per lab rules.

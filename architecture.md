# Multi-Agent Architecture & Handoff Specification

## 1. System Overview & Agent Diagram

```mermaid
flowchart TD
    User([User / Client]) --> |HTTP Request| FastAPI[FastAPI Backend / Router Layer]
    FastAPI --> Middleware[Middleware: Security, Rate Limit, RBAC]
    Middleware --> Coordinator[Coordinator Agent / Supervisor]

    subgraph RegistrySystem [Dynamic Agent Plugin Registry]
        Registry[Agent Registry] -->|Auto-Discover| BaseAgent[BaseAgent Plugin Interface]
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
| **CoordinatorAgent** | `qwen/qwen-2.5-7b-instruct` | **7B** (<= 10B) | Supervisor & Dynamic Intent Routing | AgentRegistry, Intent Evaluator | Selects specialized agent(s) dynamically |
| **KnowledgeAgent** | `qwen/qwen-2.5-7b-instruct` | **7B** (<= 10B) | RAG Semantic Search & Citations | VectorStore, Document Repository | Returns citations + confidence score |
| **WorkflowAgent** | `qwen/qwen-2.5-7b-instruct` | **7B** (<= 10B) | Procedural Step-by-Step & Mermaid Diagrams | Prompt Engine | None |
| **LearningAgent** | `qwen/qwen-2.5-7b-instruct` | **7B** (<= 10B) | Personalized Roadmaps, Quizzes & Flashcards | LearningProgress Repository | None |
| **TroubleshootingAgent** | `qwen/qwen-2.5-7b-instruct` | **7B** (<= 10B) | Operational Fault Diagnostics | Diagnostic Engine | Escalates to **TicketAgent** if confidence < 0.70 |
| **TicketAgent** | `qwen/qwen-2.5-7b-instruct` | **7B** (<= 10B) | Structured Ticket Generation | Ticket Repository | Returns Ticket ID & Escalation details |

---

## 3. Compliance & Model Specs
- **Model Name**: `qwen/qwen-2.5-7b-instruct`
- **Parameter Size**: 7 Billion parameters (strictly <= 10B limit).
- **Declaration**: Explicitly declared in source code (`backend/app/core/config.py`) and `metadata.json`.
- **Environment**: Excluded from `.env` file per lab rules.

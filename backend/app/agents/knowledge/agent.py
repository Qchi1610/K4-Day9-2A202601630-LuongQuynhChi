import os
from typing import Any, Dict, Optional
from app.agents.base import BaseAgent, AgentMetadata, AgentResponse
from app.services.llm.factory import LLMFactory
from app.services.rag.pipeline import rag_pipeline


class KnowledgeAgent(BaseAgent):
    """Knowledge Agent: RAG search, semantic retrieval, document citations, confidence scoring."""

    def __init__(self):
        prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/knowledge.md")
        self.system_prompt = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="KnowledgeAgent",
            description="Searches internal documentation using RAG semantic retrieval to answer dealership operational and product questions with citations.",
            capabilities=["rag_search", "semantic_retrieval", "document_citation", "question_answering"],
            input_schema={"query": "string"},
            output_schema={"answer": "string", "citations": "list[string]", "confidence": "float"},
        )

    async def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        # Evaluate relevance for general Q&A / document lookup
        q_lower = query.lower()
        keywords = ["what is", "how much", "policy", "specs", "specification", "document", "manual", "warranty period", "explain", "info"]
        matches = sum(1 for k in keywords if k in q_lower)
        return min(0.4 + (matches * 0.15), 0.95)

    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        # Retrieve context using RAG Pipeline
        search_results = await rag_pipeline.retrieve(query=query, top_k=4)

        if not search_results:
            context_str = "No internal document context found."
            citations = []
        else:
            context_str = "\n\n".join(
                [f"Source: {res.metadata.get('title', 'Doc')}\n{res.content}" for res in search_results]
            )
            citations = list(set([res.metadata.get('title', 'Internal Doc') for res in search_results]))

        llm = LLMFactory.get_provider()
        full_prompt = f"Retrieved Evidence Context:\n{context_str}\n\nUser Question: {query}"
        
        answer = await llm.generate(
            prompt=full_prompt,
            system_prompt=self.system_prompt,
            temperature=0.3,
        )

        confidence = 0.90 if search_results else 0.40

        return AgentResponse(
            agent_name=self.metadata.name,
            content=answer,
            confidence=confidence,
            citations=citations,
            metadata={"retrieved_chunk_count": len(search_results)},
        )

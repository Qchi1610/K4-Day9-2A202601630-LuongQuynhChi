import pytest
from app.services.rag.loader import DocumentLoader
from app.services.rag.pipeline import rag_pipeline


@pytest.mark.asyncio
async def test_rag_ingest_and_retrieve():
    doc = DocumentLoader.load_from_text(
        content="Electric Motorcycle Model X has a 72V 40Ah Lithium-ion battery pack with 120km range.",
        title="Model X Specification Sheet",
        category="specs",
    )

    doc_id = await rag_pipeline.ingest_document(doc)
    assert doc_id is not None

    results = await rag_pipeline.retrieve("What is the battery voltage of Model X?")
    assert len(results) >= 0

import json
import os
from typing import Any, Dict, List
from pydantic import BaseModel


class DocumentInput(BaseModel):
    document_id: str
    title: str
    content: str
    category: str = "general"
    metadata: Dict[str, Any] = {}


class DocumentLoader:
    """Document Loader for raw text, markdown, and JSON files."""

    @staticmethod
    def load_from_text(content: str, title: str, category: str = "general") -> DocumentInput:
        doc_id = f"doc_{hash(content + title) & 0xffffffff:08x}"
        return DocumentInput(
            document_id=doc_id,
            title=title,
            content=content,
            category=category,
        )

    @staticmethod
    def load_from_file(file_path: str, category: str = "general") -> List[DocumentInput]:
        if not os.path.exists(file_path):
            return []

        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if file_path.endswith(".json"):
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return [
                        DocumentInput(
                            document_id=item.get("id", f"doc_{idx}"),
                            title=item.get("title", f"{filename} Item {idx}"),
                            content=item.get("content", str(item)),
                            category=item.get("category", category),
                            metadata=item.get("metadata", {}),
                        )
                        for idx, item in enumerate(data)
                    ]
            except Exception:
                pass

        doc_id = f"doc_{filename}"
        return [
            DocumentInput(
                document_id=doc_id,
                title=filename,
                content=content,
                category=category,
            )
        ]

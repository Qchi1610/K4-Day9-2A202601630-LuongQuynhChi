from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel
from app.services.database.connection import db_manager

T = TypeVar("T", bound=BaseModel)


class BaseRepository:
    """Generic Repository Pattern supporting both MongoDB Motor and fallback in-memory store."""

    def __init__(self, collection_name: str, id_field: str, model_cls: Type[T]):
        self.collection_name = collection_name
        self.id_field = id_field
        self.model_cls = model_cls
        self._in_memory: Dict[str, Dict[str, Any]] = {}

    async def insert(self, entity: T) -> T:
        data = entity.model_dump(mode="json")
        entity_id = str(data.get(self.id_field))

        collection = db_manager.get_collection(self.collection_name)
        if collection is not None:
            await collection.update_one(
                {self.id_field: entity_id}, {"$set": data}, upsert=True
            )
        else:
            self._in_memory[entity_id] = data

        return entity

    async def get_by_id(self, entity_id: str) -> Optional[T]:
        collection = db_manager.get_collection(self.collection_name)
        if collection is not None:
            doc = await collection.find_one({self.id_field: entity_id})
            if doc:
                doc.pop("_id", None)
                return self.model_cls.model_validate(doc)
            return None

        if entity_id in self._in_memory:
            return self.model_cls.model_validate(self._in_memory[entity_id])
        return None

    async def find_all(self, query: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[T]:
        query = query or {}
        collection = db_manager.get_collection(self.collection_name)
        if collection is not None:
            cursor = collection.find(query).limit(limit)
            results = []
            async for doc in cursor:
                doc.pop("_id", None)
                results.append(self.model_cls.model_validate(doc))
            return results

        results = []
        for doc in list(self._in_memory.values())[:limit]:
            match = all(doc.get(k) == v for k, v in query.items())
            if match:
                results.append(self.model_cls.model_validate(doc))
        return results

    async def update(self, entity_id: str, updates: Dict[str, Any]) -> Optional[T]:
        collection = db_manager.get_collection(self.collection_name)
        if collection is not None:
            await collection.update_one({self.id_field: entity_id}, {"$set": updates})
            return await self.get_by_id(entity_id)

        if entity_id in self._in_memory:
            self._in_memory[entity_id].update(updates)
            return self.model_cls.model_validate(self._in_memory[entity_id])
        return None

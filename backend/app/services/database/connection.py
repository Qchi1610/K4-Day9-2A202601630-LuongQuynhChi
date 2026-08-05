try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    HAS_MOTOR = True
except ImportError:
    AsyncIOMotorClient = None
    AsyncIOMotorDatabase = None
    HAS_MOTOR = False

from app.core.config import settings
from app.core.logging import logger


class DatabaseManager:
    """MongoDB Async Motor Connection Manager with mock/in-memory fallback."""

    client: Optional[Any] = None
    db: Optional[Any] = None
    _in_memory_store: Dict[str, Dict[str, Any]] = {}

    @classmethod
    async def connect(cls):
        if not HAS_MOTOR:
            logger.warning("Motor MongoDB driver not available. Operating in active in-memory repository store mode.")
            return

        try:
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=1000,
            )
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            await cls.client.admin.command("ping")
            logger.info(f"Successfully connected to MongoDB at {settings.MONGODB_URL}")
        except Exception as e:
            logger.warning(
                f"MongoDB connection failed ({e}). Falling back to active in-memory repository store."
            )
            cls.client = None
            cls.db = None

    @classmethod
    async def disconnect(cls):
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("MongoDB client disconnected.")

    @classmethod
    def get_collection(cls, collection_name: str):
        if cls.db is not None:
            return cls.db[collection_name]
        return None


db_manager = DatabaseManager()

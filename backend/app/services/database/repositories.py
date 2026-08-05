from app.models.chat_log import ChatLogModel
from app.models.document import DocumentModel
from app.models.learning_progress import LearningProgressModel
from app.models.session import SessionModel
from app.models.ticket import TicketModel
from app.models.user import UserModel
from app.services.database.base_repository import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_name="users", id_field="user_id", model_cls=UserModel)


class SessionRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_name="sessions", id_field="session_id", model_cls=SessionModel)


class DocumentRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_name="documents", id_field="document_id", model_cls=DocumentModel)


class TicketRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_name="tickets", id_field="ticket_id", model_cls=TicketModel)


class ChatLogRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_name="chat_logs", id_field="log_id", model_cls=ChatLogModel)


class LearningProgressRepository(BaseRepository):
    def __init__(self):
        super().__init__(
            collection_name="learning_progress", id_field="progress_id", model_cls=LearningProgressModel
        )


user_repo = UserRepository()
session_repo = SessionRepository()
document_repo = DocumentRepository()
ticket_repo = TicketRepository()
chat_log_repo = ChatLogRepository()
learning_progress_repo = LearningProgressRepository()

"""Infrastructure layer package for Web Backend."""

from web_backend.infra.ai_client.remote_ai_client import RemoteAiClient
from web_backend.infra.database.connection import get_connection, init_db

__all__ = [
    "get_connection",
    "init_db",
    "RemoteAiClient",
]

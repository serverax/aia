import os


class Config:
    QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
    QDRANT_PORT = os.environ.get("QDRANT_PORT", "6333")
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
    RAG_SERVICE_URL = os.environ.get("RAG_SERVICE_URL", "http://localhost:8000")
    ANALYST_SERVICE_URL = os.environ.get("ANALYST_SERVICE_URL", "http://localhost:8001")
    SEMANTIC_SEARCH_URL = os.environ.get("SEMANTIC_SEARCH_URL", "http://localhost:8002")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "mock_key")

mkdir -p /app/services/rag_system
echo "class SentenceTransformer: pass" > /app/services/rag_system/mock_transformer.py
sed -i 's/from sentence_transformers import SentenceTransformer/from .mock_transformer import SentenceTransformer/' /app/services/rag_system/rag_system.py
export PYTHONPATH=/app
export QDRANT_HOST=qdrant.data-layer
export REDIS_HOST=redis.ordinox-ai
python3 -m services.analyst_agent.analyst_service --host 0.0.0.0 --port 8000

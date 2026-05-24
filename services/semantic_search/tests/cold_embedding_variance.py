import time
import statistics
import asyncio
from services.semantic_search.embedding.embedder import Embedder
from services.semantic_search.knowledge_base.sample_data import SAMPLE_DOCUMENTS


async def test_cold_embedding_variance():
    print("Testing Cold Embedding Variance (5 runs, 50 docs per run)...")
    docs = [doc.content for doc in SAMPLE_DOCUMENTS]

    # Pre-load model once
    embedder = Embedder(cache_capacity=0)

    times = []
    for i in range(5):
        start = time.time()
        # Ensure we are not using internal cache by passing new list of strings if necessary,
        # but cache_capacity=0 already ensures no cache.
        embedder.embed(docs)
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        print(f"Run {i+1}: {elapsed:.2f}ms")

    print(f"\nResults:")
    print(f"Min: {min(times):.2f}ms")
    print(f"Max: {max(times):.2f}ms")
    print(f"Avg: {statistics.mean(times):.2f}ms")
    print(f"StdDev: {statistics.stdev(times):.2f}ms")


if __name__ == "__main__":
    asyncio.run(test_cold_embedding_variance())

import asyncio
import json
import statistics
import time

from services.semantic_search.embedding.embedder import Embedder
from services.semantic_search.knowledge_base.sample_data import SAMPLE_DOCUMENTS
from services.semantic_search.knowledge_base.store_manager import KnowledgeBaseManager
from services.semantic_search.search.semantic_search import SemanticSearchEngine
from services.semantic_search.vector_store.faiss_store import FAISSStore


async def run_benchmarks():
    print("=== Semantic Search Benchmarks ===")

    # Setup
    store = FAISSStore(dimension=384, metric="cosine")
    embedder = Embedder(cache_capacity=100)
    kb_manager = KnowledgeBaseManager(store, embedder)

    # 1. Embedding Benchmark
    print("\n[1/3] Embedding Benchmark (Batch of 50)...")
    start_time = time.time()
    kb_manager.add_documents(SAMPLE_DOCUMENTS)
    total_time = time.time() - start_time
    print(f"Total time for 50 docs: {total_time:.4f}s")
    print(f"Avg time per doc: {(total_time/50)*1000:.2f}ms")

    # 2. Search Latency Benchmark
    search_engine = SemanticSearchEngine(store, embedder)
    queries = [
        "GDPR data privacy requirements",
        "AML suspicious activity reporting",
        "Cybersecurity MFA best practices",
        "Whistleblower protection policy",
        "Liability for data breach disclosure",
    ]

    print("\n[2/3] Search Latency Benchmark (100 iterations)...")
    latencies = []
    for _ in range(20):  # 20 iterations * 5 queries
        for q in queries:
            start = time.time()
            search_engine.search(q, top_k=5)
            latencies.append(time.time() - start)

    avg_latency = statistics.mean(latencies) * 1000
    p95_latency = statistics.quantiles(latencies, n=20)[18] * 1000
    print(f"Avg Latency: {avg_latency:.2f}ms")
    print(f"P95 Latency: {p95_latency:.2f}ms")

    # 3. Task 3.3 -> Task 3.4 Integration Simulation
    print("\n[3/3] Integration Test: Task 3.3 -> Task 3.4...")
    # Mocking what the Analyst Agent would do
    risk_query = "Potential GDPR violation in EU branch"
    recommendation_context = search_engine.search(
        risk_query, top_k=2, filters={"jurisdiction": "EU"}
    )

    integration_success = (
        len(recommendation_context) > 0 and recommendation_context[0]["id"] == "POL_001"
    )
    print(f"Integration Result: {'SUCCESS' if integration_success else 'FAILED'}")
    if integration_success:
        print(f"Grounding found: {recommendation_context[0]['title']}")

    # Report structure
    report = {
        "benchmarks": {
            "embedding_avg_ms": round(total_time / 50 * 1000, 2),
            "search_avg_ms": round(avg_latency, 2),
            "search_p95_ms": round(p95_latency, 2),
        },
        "integration": "Verified" if integration_success else "Failed",
    }

    with open("F:/aia/sprint3_performance_report.json", "w") as f:
        json.dump(report, f, indent=4)


if __name__ == "__main__":
    asyncio.run(run_benchmarks())

import asyncio
import json
import os
import platform
import statistics
import time

import psutil

from services.analyst_agent.analyst_agent import DomainAnalystAgent
from services.semantic_search.embedding.embedder import Embedder
from services.semantic_search.knowledge_base.sample_data import SAMPLE_DOCUMENTS
from services.semantic_search.knowledge_base.store_manager import KnowledgeBaseManager
from services.semantic_search.search.semantic_search import SemanticSearchEngine
from services.semantic_search.vector_store.faiss_store import FAISSStore


def get_hardware_info():
    return {
        "cpu": platform.processor(),
        "cores": psutil.cpu_count(logical=False),
        "threads": psutil.cpu_count(logical=True),
        "ram": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "os": platform.system(),
    }


async def run_detailed_benchmarks():
    print("=== Detailed Sprint 3 Benchmarks ===")
    hw = get_hardware_info()
    print(f"Hardware: {hw['cpu']} | {hw['ram']} RAM | {hw['threads']} Threads")

    # Setup
    store = FAISSStore(dimension=384, metric="cosine")
    embedder = Embedder(cache_capacity=1000)  # Large cache to test warm vs cold
    kb_manager = KnowledgeBaseManager(store, embedder)

    # 1. Embedding Benchmark (Cold vs Warm)
    print("\n[1/4] Embedding Benchmark (50 docs)...")

    # Cold (No Cache)
    start_time = time.time()
    kb_manager.add_documents(SAMPLE_DOCUMENTS)
    cold_time = time.time() - start_time

    # Warm (All Cached)
    start_time = time.time()
    kb_manager.add_documents(SAMPLE_DOCUMENTS)  # Should hit cache
    warm_time = time.time() - start_time

    print(
        f"Cold Embedding (Batch 50): {cold_time*1000:.2f}ms total (avg {cold_time*1000/50:.2f}ms/doc)"
    )
    print(
        f"Warm Embedding (Batch 50): {warm_time*1000:.2f}ms total (avg {warm_time*1000/50:.2f}ms/doc)"
    )

    # 2. Search Latency Benchmark (30 runs, P50/P95/P99)
    search_engine = SemanticSearchEngine(store, embedder)
    queries = [
        "data privacy in the EU",
        "suspicious money laundering",
        "mfa security guidelines",
        "reporting unethical behavior",
        "fine for data breach",
    ]

    print("\n[2/4] Search Latency Benchmark (30 runs x 5 queries)...")
    latencies = []
    for _ in range(30):
        for q in queries:
            start = time.time()
            search_engine.search(q, top_k=5)
            latencies.append(time.time() - start)

    latencies_ms = [l * 1000 for l in latencies]
    p50 = statistics.median(latencies_ms)
    p95 = statistics.quantiles(latencies_ms, n=20)[18]
    p99 = statistics.quantiles(latencies_ms, n=100)[98]

    print(f"P50 Latency: {p50:.2f}ms")
    print(f"P95 Latency: {p95:.2f}ms")
    print(f"P99 Latency: {p99:.2f}ms")

    # 3. Memory Measurement
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    rss_mb = mem_info.rss / (1024 * 1024)
    print(f"\n[3/4] Memory Footprint: {rss_mb:.2f} MB (Current Process RSS)")

    # 4. Integration Expansion (5 queries)
    print("\n[4/4] Integration Tests (5 Queries)...")
    agent = DomainAnalystAgent()
    # Need to point agent to local RAG system, but for benchmarking we'll use search engine directly
    # as the 'grounding' layer is what we're testing.

    integration_queries = [
        {"q": "What are the data privacy rules in Europe?", "expected": "POL_001"},
        {"q": "How to report suspicious financial activity?", "expected": "POL_002"},
        {"q": "Requirements for multi-factor authentication?", "expected": "GUI_001"},
        {"q": "Legal consequences of not disclosing a breach?", "expected": "CAS_001"},
        {"q": "Anonymity for reporting unethical behavior?", "expected": "POL_003"},
    ]

    results = []
    for test in integration_queries:
        res = search_engine.search(test["q"], top_k=1)
        match = res[0]["id"] == test["expected"] if res else False
        print(
            f"Query: {test['q'][:40]}... -> Result: {res[0]['id'] if res else 'NONE'} [{'SUCCESS' if match else 'FAILED'}]"
        )
        results.append(match)

    print(f"Overall Integration Success: {sum(results)}/5")

    # Final detailed report
    full_report = {
        "hardware": hw,
        "embedding": {
            "cold_batch_50_ms": round(cold_time * 1000, 2),
            "warm_batch_50_ms": round(warm_time * 1000, 2),
        },
        "search_latency": {"p50": round(p50, 2), "p95": round(p95, 2), "p99": round(p99, 2)},
        "memory_rss_mb": round(rss_mb, 2),
        "integration_tests": f"{sum(results)}/5",
    }

    with open("F:/aia/detailed_sprint3_report.json", "w") as f:
        json.dump(full_report, f, indent=4)


if __name__ == "__main__":
    asyncio.run(run_detailed_benchmarks())

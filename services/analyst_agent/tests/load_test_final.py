import asyncio
import time
import statistics
import httpx
import websockets
import json
import psutil
import os

# Configuration
API_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001/ws/hitl"
CONCURRENT_USERS = 20
TOTAL_REQUESTS = 100


async def test_rest_load():
    print(
        f"\n[1/2] REST Load Test: {TOTAL_REQUESTS} requests across {CONCURRENT_USERS} concurrent users..."
    )
    latencies = []

    async def make_request(client):
        payload = {
            "request_type": "policy_change",
            "title": "Load Test",
            "description": "testing",
            "requestor": "tester",
            "deadline": "2026-01-01",
        }
        start = time.time()
        try:
            resp = await client.post(
                f"{API_URL}/analyst/approval/evaluate", json=payload, timeout=30
            )
            if resp.status_code == 200:
                latencies.append(time.time() - start)
            else:
                print(f"Request failed with status {resp.status_code}")
        except Exception as e:
            print(f"Request failed: {e}")

    async with httpx.AsyncClient() as client:
        for i in range(0, TOTAL_REQUESTS, CONCURRENT_USERS):
            batch = [make_request(client) for _ in range(CONCURRENT_USERS)]
            await asyncio.gather(*batch)

    latencies_ms = [l * 1000 for l in latencies]
    return {
        "p50": statistics.median(latencies_ms) if latencies_ms else 0,
        "p95": (
            statistics.quantiles(latencies_ms, n=20)[18]
            if len(latencies_ms) >= 20
            else max(latencies_ms or [0])
        ),
        "p99": (
            statistics.quantiles(latencies_ms, n=100)[98]
            if len(latencies_ms) >= 100
            else max(latencies_ms or [0])
        ),
        "total_requests": len(latencies),
    }


async def test_websocket_broadcast_load():
    print(f"\n[2/2] WebSocket Load Test: 50 concurrent listeners...")
    NUM_LISTENERS = 50
    results = [False] * NUM_LISTENERS

    async def listen(idx):
        try:
            async with websockets.connect(WS_URL) as ws:
                # Wait for any broadcast message
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                if msg:
                    results[idx] = True
        except Exception as e:
            # print(f"Listener {idx} failed: {e}")
            pass

    # Start listeners
    tasks = [asyncio.create_task(listen(i)) for i in range(NUM_LISTENERS)]
    await asyncio.sleep(3)  # Increased stabilization time

    # Trigger a broadcast via analyze endpoint
    print("Triggering broadcast...")
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_URL}/analyst/analyze", json={"query": "broadcast test"}, timeout=30
        )

    # Wait for all listeners to finish or timeout
    await asyncio.gather(*tasks, return_exceptions=True)

    received_count = sum(results)
    return {"listeners": NUM_LISTENERS, "messages_received": received_count}


def get_server_memory():
    total_rss = 0
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info["cmdline"] or [])
            if "analyst_service" in cmdline or "semantic_search.api.main" in cmdline:
                total_rss += proc.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total_rss / (1024 * 1024)


async def run_full_load_suite():
    print("=== GEMINI LOAD TESTING SUITE (FINAL) ===")

    rest_stats = await test_rest_load()
    ws_stats = await test_websocket_broadcast_load()
    server_mem = get_server_memory()

    report = f"""# GEMINI BASELINE PERFORMANCE REPORT

## Hardware Context
- CPU Threads: {psutil.cpu_count(logical=True)}
- Memory: {round(psutil.virtual_memory().total / (1024**3), 2)} GB

## [1] REST API Performance (Analyst Service)
- **Concurrency**: {CONCURRENT_USERS} Users
- **Total Requests**: {TOTAL_REQUESTS}
- **P50 Latency**: {rest_stats['p50']:.2f}ms
- **P95 Latency**: {rest_stats['p95']:.2f}ms
- **P99 Latency**: {rest_stats['p99']:.2f}ms
- **Success Rate**: {(rest_stats['total_requests']/TOTAL_REQUESTS)*100:.1f}%

## [2] WebSocket Event Hub Performance
- **Concurrent Connections**: {ws_stats['listeners']}
- **Total Event Broadcasts Received**: {ws_stats['messages_received']}
- **Success Rate**: {(ws_stats['messages_received']/ws_stats['listeners'])*100:.1f}%
- **Observation**: Real-time dashboard synchronization verified for {ws_stats['messages_received']} active observers.

## Memory Stability
- Total Server Stack RSS (Analyst + Search): {server_mem:.2f} MB
"""

    with open("F:/aia/GEMINI_BASELINE_PERFORMANCE.md", "w") as f:
        f.write(report)

    print("\n✅ Load Testing Complete. Report saved to GEMINI_BASELINE_PERFORMANCE.md")
    print(report)


if __name__ == "__main__":
    asyncio.run(run_full_load_suite())

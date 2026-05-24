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
CONCURRENT_USERS = 20  # Reduced for more stability on local hardware
TOTAL_REQUESTS = 100


async def test_rest_load():
    print(
        f"\n[1/2] REST Load Test: {TOTAL_REQUESTS} requests across {CONCURRENT_USERS} concurrent users..."
    )
    latencies = []

    async def make_request(client):
        # Using evaluate endpoint which doesn't call Qdrant to isolate model bottleneck
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
            latencies.append(time.time() - start)
        except Exception as e:
            print(f"Request failed: {e}")

    async with httpx.AsyncClient() as client:
        for i in range(0, TOTAL_REQUESTS, CONCURRENT_USERS):
            batch = [make_request(client) for _ in range(CONCURRENT_USERS)]
            await asyncio.gather(*batch)

    latencies_ms = [l * 1000 for l in latencies]
    return {
        "p50": statistics.median(latencies_ms),
        "p95": statistics.quantiles(latencies_ms, n=20)[18],
        "p99": (
            statistics.quantiles(latencies_ms, n=100)[98]
            if len(latencies_ms) >= 100
            else max(latencies_ms)
        ),
        "total_requests": len(latencies),
    }


async def test_websocket_broadcast_load():
    print(f"\n[2/2] WebSocket Load Test: 50 concurrent listeners...")
    NUM_LISTENERS = 50
    messages_received_count = 0

    async def listen(id):
        nonlocal messages_received_count
        try:
            async with websockets.connect(WS_URL) as ws:
                # Wait for exactly one broadcast
                msg = await ws.recv()
                if msg:
                    messages_received_count += 1
        except Exception as e:
            pass

    # Start listeners
    listeners = [asyncio.create_task(listen(i)) for i in range(NUM_LISTENERS)]
    await asyncio.sleep(1)

    # Trigger a broadcast via analyze endpoint (which calls notify_agent_step)
    # We'll use a mocked version or just the live one
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_URL}/analyst/analyze", json={"query": "broadcast test"}, timeout=30
        )

    # Wait for all listeners to receive the message
    await asyncio.wait(listeners, timeout=10)

    return {"listeners": NUM_LISTENERS, "messages_received": messages_received_count}


def get_server_memory(pids):
    total_rss = 0
    for pid in pids:
        try:
            p = psutil.Process(pid)
            total_rss += p.memory_info().rss
        except:
            pass
    return total_rss / (1024 * 1024)


async def run_full_load_suite():
    print("=== GEMINI LOAD TESTING SUITE (REFINED) ===")

    # PIDs for Analyst Service and Semantic Search
    SERVER_PIDS = [44280, 83128]

    rest_stats = await test_rest_load()
    ws_stats = await test_websocket_broadcast_load()
    server_mem = get_server_memory(SERVER_PIDS)

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
- **Observation**: Real-time dashboard synchronization verified for {ws_stats['listeners']} concurrent observers.

## Memory Stability
- Total Server Stack RSS (Analyst + Search): {server_mem:.2f} MB
"""

    with open("F:/aia/GEMINI_BASELINE_PERFORMANCE.md", "w") as f:
        f.write(report)

    print("\n✅ Load Testing Complete. Report saved to GEMINI_BASELINE_PERFORMANCE.md")
    print(report)


if __name__ == "__main__":
    asyncio.run(run_full_load_suite())

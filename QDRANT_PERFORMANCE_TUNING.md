# Qdrant Performance Tuning & Optimization

## Local Profiling Results
- **Search Latency (Mean)**: 3.03ms (Warm Cache)
- **Search Latency (P99)**: 50.93ms
- **Memory RSS**: ~540MB (Base Model + Small Index)

## Production Recommendations

### [1] Batch Ingestion
- **Strategy**: Do NOT insert documents one-by-one.
- **Batch Size**: 64-128 vectors per request for optimal throughput.
- **Parallelism**: Use 4-8 parallel ingestion workers to saturate CPU during initial indexing.

### [2] Vector Store Indexing
- **HNSW Parameters**:
  - `m`: 16 (default)
  - `ef_construct`: 100
- **Segment Optimization**: Trigger manual segment optimization after bulk loads to reduce search latency by ~15%.

### [3] Resource Allocation (Talos)
- **CPU**: 2.0 Cores (min) / 4.0 Cores (limit)
- **Memory**: 4Gi RAM (minimum for `all-MiniLM-L6-v2` + 50k vectors)
- **Storage**: SSD/NVMe required for low-latency persistence.

### [4] Payload Optimization
- **Filtering**: Always use `payload` indexing for metadata fields like `jurisdiction` and `risk_category`.
- **Projection**: Retrieve only necessary fields in search results to minimize I/O.

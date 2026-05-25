import json
import os
from typing import Any, Dict, List

import faiss
import numpy as np

from .schemas import SearchResult, VectorItem


class FAISSStore:
    def __init__(self, dimension: int = 384, metric: str = "cosine", index_path: str = None):
        self.dimension = dimension
        self.metric = metric
        self.index_path = index_path

        if metric == "cosine":
            # Cosine similarity is equivalent to L2 on normalized vectors
            self.index = faiss.IndexFlatIP(dimension)
            self.index = faiss.IndexIDMap(self.index)
        else:  # L2
            self.index = faiss.IndexFlatL2(dimension)
            self.index = faiss.IndexIDMap(self.index)

        self.metadata_store: Dict[str, Dict[str, Any]] = {}
        self.id_map: Dict[int, str] = {}  # int -> str ID
        self.str_to_int_id: Dict[str, int] = {}  # str -> int ID
        self.next_int_id = 0

        if index_path and os.path.exists(index_path):
            self.load(index_path)

    def _normalize(self, vector: np.ndarray) -> np.ndarray:
        """Normalize vector for cosine similarity."""
        faiss.normalize_L2(vector)
        return vector

    def add(self, items: List[VectorItem]):
        """Add vectors and metadata to the store."""
        vectors = []
        ids = []

        for item in items:
            # Map string ID to unique integer ID
            if item.id not in self.str_to_int_id:
                int_id = self.next_int_id
                self.next_int_id += 1
                self.str_to_int_id[item.id] = int_id
                self.id_map[int_id] = item.id

            int_id = self.str_to_int_id[item.id]
            ids.append(int_id)

            vec = np.array(item.vector).astype("float32").reshape(1, -1)
            if self.metric == "cosine":
                vec = self._normalize(vec)
            vectors.append(vec)

            self.metadata_store[item.id] = item.metadata

        if vectors:
            vectors_np = np.vstack(vectors)
            ids_np = np.array(ids).astype("int64")
            self.index.add_with_ids(vectors_np, ids_np)

    def search(
        self, query_vector: List[float], top_k: int = 10, filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Search for similar vectors, optionally applying metadata filters."""
        vec = np.array(query_vector).astype("float32").reshape(1, -1)
        if self.metric == "cosine":
            vec = self._normalize(vec)

        # If filters are present, we might need a larger initial k to filter down
        search_k = top_k * 5 if filters else top_k
        scores, int_ids = self.index.search(vec, search_k)

        results = []
        for score, int_id in zip(scores[0], int_ids[0]):
            if int_id == -1:
                continue

            str_id = self.id_map.get(int_id)
            if not str_id:
                continue

            metadata = self.metadata_store.get(str_id, {})

            # Apply filters
            if filters:
                match = True
                for key, value in filters.items():
                    if metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            results.append(SearchResult(id=str_id, score=float(score), metadata=metadata))

            if len(results) >= top_k:
                break

        return results

    def delete(self, ids: List[str]):
        """Remove vectors from the index by ID."""
        int_ids = []
        for str_id in ids:
            if str_id in self.str_to_int_id:
                int_id = self.str_to_int_id[str_id]
                int_ids.append(int_id)
                del self.str_to_int_id[str_id]
                del self.id_map[int_id]
                if str_id in self.metadata_store:
                    del self.metadata_store[str_id]

        if int_ids:
            self.index.remove_ids(np.array(int_ids).astype("int64"))

    def save(self, path: str):
        """Persist index and metadata to disk."""
        if not os.path.exists(path):
            os.makedirs(path)

        faiss.write_index(self.index, os.path.join(path, "index.faiss"))

        data = {
            "metadata_store": self.metadata_store,
            "id_map": self.id_map,
            "str_to_int_id": self.str_to_int_id,
            "next_int_id": self.next_int_id,
            "dimension": self.dimension,
            "metric": self.metric,
        }
        with open(os.path.join(path, "data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load(self, path: str):
        """Load index and metadata from disk."""
        self.index = faiss.read_index(os.path.join(path, "index.faiss"))

        data_json_path = os.path.join(path, "data.json")
        if not os.path.exists(data_json_path):
            raise FileNotFoundError(
                f"Missing metadata file: {data_json_path}. "
                "Legacy pickle metadata is no longer loaded for security reasons."
            )

        with open(data_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.metadata_store = data["metadata_store"]
        # JSON object keys are strings; convert integer IDs back.
        self.id_map = {int(k): v for k, v in data["id_map"].items()}
        self.str_to_int_id = {k: int(v) for k, v in data["str_to_int_id"].items()}
        self.next_int_id = int(data["next_int_id"])
        self.dimension = int(data["dimension"])
        self.metric = data["metric"]

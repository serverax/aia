import collections
from typing import Dict, List, Optional


class LRUCache:
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache = collections.OrderedDict()

    def get(self, key: str) -> Optional[List[float]]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: List[float]):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


class EmbeddingCache:
    def __init__(self, capacity: int = 1000):
        self.cache = LRUCache(capacity)
        self.hits = 0
        self.misses = 0

    def get_embedding(self, text: str) -> Optional[List[float]]:
        val = self.cache.get(text)
        if val:
            self.hits += 1
        else:
            self.misses += 1
        return val

    def set_embedding(self, text: str, embedding: List[float]):
        self.cache.put(text, embedding)

    def get_stats(self):
        return {"hits": self.hits, "misses": self.misses}

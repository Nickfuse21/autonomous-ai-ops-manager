from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class MemoryItem:
    vector: List[float]
    payload: Dict[str, Any]


class DecisionMemoryStore:
    def __init__(self, storage_path: str | None = None) -> None:
        self._items: List[MemoryItem] = []
        default_path = Path(__file__).resolve().parents[2] / "storage" / "memory.json"
        self._storage_path = Path(storage_path) if storage_path else default_path
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _embed(self, text: str) -> List[float]:
        # Simple deterministic embedding for local MVP.
        vec = [0.0] * 32
        for idx, ch in enumerate(text.lower()):
            vec[idx % 32] += (ord(ch) % 31) / 31.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def add(self, context_text: str, payload: Dict[str, Any]) -> None:
        self._items.append(MemoryItem(vector=self._embed(context_text), payload=payload))
        self._persist()

    def search(self, context_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        query = self._embed(context_text)
        scored: List[tuple[float, Dict[str, Any]]] = []
        for item in self._items:
            score = sum(a * b for a, b in zip(query, item.vector))
            scored.append((score, item.payload))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"similarity": round(score, 4), "payload": payload}
            for score, payload in scored[:top_k]
        ]

    def _persist(self) -> None:
        serializable = [
            {"vector": item.vector, "payload": item.payload}
            for item in self._items
        ]
        self._storage_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._items = [MemoryItem(vector=item["vector"], payload=item["payload"]) for item in raw]
        except Exception:
            self._items = []

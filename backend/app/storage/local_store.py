from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class LocalAuditStore:
    """
    Beginner-friendly local storage.
    Persists decision summaries in a JSON file so data survives app restart.
    """

    def __init__(self, file_path: str | None = None) -> None:
        default_path = Path(__file__).resolve().parents[2] / "storage" / "audit_log.json"
        self.file_path = Path(file_path) if file_path else default_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def read_all(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            return []
        try:
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def append(self, record: Dict[str, Any]) -> None:
        records = self.read_all()
        records.append(record)
        self.file_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

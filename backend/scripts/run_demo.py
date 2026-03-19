from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app


def main() -> None:
    client = TestClient(app)
    resp = client.post("/api/cycle/demo")
    resp.raise_for_status()
    payload = resp.json()
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

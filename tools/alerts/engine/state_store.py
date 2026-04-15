from __future__ import annotations

import json
from pathlib import Path


class JsonStateStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({'keys': {}}, indent=2))

    def load(self) -> dict:
        return json.loads(self.path.read_text())

    def save(self, data: dict):
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def get(self, key: str) -> dict:
        data = self.load()
        return (data.get('keys') or {}).get(key, {})

    def set(self, key: str, value: dict):
        data = self.load()
        data.setdefault('keys', {})[key] = value
        self.save(data)

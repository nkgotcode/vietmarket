from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=4)
def _validator(schema_path: str):
    import jsonschema  # type: ignore
    schema = json.loads(Path(schema_path).read_text())
    return jsonschema.Draft202012Validator(schema)


def validate_event(event: dict, schema_path: str) -> tuple[bool, str | None]:
    v = _validator(schema_path)
    errs = sorted(v.iter_errors(event), key=lambda e: list(e.path))
    if not errs:
        return True, None
    e = errs[0]
    loc = '.'.join(map(str, e.absolute_path)) or '<root>'
    return False, f"{loc}: {e.message}"

from __future__ import annotations

import json

from packages.supervisor.common.db import connect

DEFAULT_PROMPTS = {
    'phase4_thesis_packet': 'Deterministic Phase 4 thesis prompt packet v1',
    'phase4_recommendation_packet': 'Deterministic Phase 4 recommendation prompt packet v1',
}


def ensure_default_prompts() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            for name, text in DEFAULT_PROMPTS.items():
                cur.execute(
                    '''
                    INSERT INTO prompt_versions (prompt_name, prompt_version, prompt_text, created_at, updated_at)
                    VALUES (%s,%s,%s,now(),now())
                    ON CONFLICT (prompt_name) DO UPDATE SET
                      prompt_version = EXCLUDED.prompt_version,
                      prompt_text = EXCLUDED.prompt_text,
                      updated_at = now()
                    ''',
                    (name, 'v1', text),
                )


def get_prompt(name: str) -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT prompt_name, prompt_version, prompt_text, updated_at FROM prompt_versions WHERE prompt_name = %s LIMIT 1', (name,))
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f'prompt_not_found:{name}')
            return {'prompt_name': row[0], 'prompt_version': row[1], 'prompt_text': row[2], 'updated_at': row[3].isoformat() if row[3] else None}

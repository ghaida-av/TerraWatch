"""In-process evidence store (bounded LRU).

Why: the LLM should see compact `measurements`, but the analysis engine needs every row
(`observations`). Tools return the compact view + `evidence_id`; analysis calls
`get_evidence(evidence_id)` to get the full object. IDs are content hashes, so sharing across
concurrent investigations is harmless.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional

from data.schemas.models import Evidence

_MAX = 500
_store: "OrderedDict[str, Evidence]" = OrderedDict()
_lock = threading.Lock()


def put(evidence: Evidence) -> None:
    with _lock:
        _store[evidence.evidence_id] = evidence
        _store.move_to_end(evidence.evidence_id)
        while len(_store) > _MAX:
            _store.popitem(last=False)


def get_evidence(evidence_id: str) -> Optional[Evidence]:
    with _lock:
        ev = _store.get(evidence_id)
        if ev is not None:
            _store.move_to_end(evidence_id)
        return ev


def clear() -> None:
    with _lock:
        _store.clear()

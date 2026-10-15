"""Append-only audit trail at output/audit_trail.json (a JSON array; never wiped)."""

import json
import threading
from datetime import datetime, timezone
from typing import Any

from .config import AUDIT_PATH, AUDIT_TEXT_LIMIT, MODEL_NAME
from .models import AuditEntry, TeamDeps

_lock = threading.Lock()


def clip(value: Any) -> Any:
    """Keep audit entries readable: long strings are cut, everything else is made JSON-safe."""
    if isinstance(value, str):
        return value if len(value) <= AUDIT_TEXT_LIMIT else value[:AUDIT_TEXT_LIMIT] + "...[cut]"
    if isinstance(value, dict):
        return {str(k): clip(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clip(v) for v in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return clip(str(value))


def usage_dict(usage: Any) -> dict[str, int] | None:
    if usage is None:
        return None
    return {k: int(getattr(usage, k, 0) or 0)
            for k in ("requests", "tool_calls", "input_tokens", "output_tokens")}


def record(deps: TeamDeps, event: str, details: dict[str, Any] | None = None, *,
           step: int | None = None, usage: Any = None) -> None:
    entry = AuditEntry(
        ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        run_id=deps.shared.run_id,
        agent=deps.role,
        chain=list(deps.chain),
        depth=deps.depth,
        ticket_id=deps.ticket_id,
        step=step,
        event=event,
        model=MODEL_NAME,
        details=clip(details or {}),
        usage=usage_dict(usage),
    )
    _append(entry)


def record_action(actor: str, event: str, details: dict[str, Any], *,
                  run_id: str = "dashboard", ticket_id: int | None = None) -> None:
    """Audit an action taken by a human or the API (approve, reject, reset), not an agent."""
    _append(AuditEntry(
        ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        run_id=run_id, agent=actor, chain=[], depth=0, ticket_id=ticket_id,
        event=event, details=clip(details),
    ))


def read_all() -> list[dict[str, Any]]:
    with _lock:
        if not AUDIT_PATH.exists() or not AUDIT_PATH.stat().st_size:
            return []
        return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def _append(entry: AuditEntry) -> None:
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        entries: list = []
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size:
            entries = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                raise RuntimeError(f"{AUDIT_PATH} is not a JSON array; refusing to overwrite it.")
        entries.append(entry.model_dump())
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        tmp.replace(AUDIT_PATH)

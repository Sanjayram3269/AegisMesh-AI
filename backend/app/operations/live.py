"""Bounded, ephemeral execution telemetry. Never an authorization source."""

import time
import uuid
from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from threading import RLock

_current = ContextVar("aegis_live_run", default=None)


class RunJournal:
    def __init__(self):
        self.runs = OrderedDict()
        self.lock = RLock()

    def create(self, user, operation):
        with self.lock:
            for key in list(self.runs):
                if time.time() - self.runs[key]["started_at"] > 600:
                    del self.runs[key]
            while len(self.runs) >= 200:
                self.runs.popitem(last=False)
            run_id = "LIVE-" + uuid.uuid4().hex
            self.runs[run_id] = {
                "id": run_id,
                "owner": user["username"],
                "operation": operation,
                "started_at": time.time(),
                "events": [],
                "complete": False,
                "claimed": False,
            }
            return self.read(run_id, user)

    def read(self, run_id, user):
        with self.lock:
            run = self.runs.get(run_id)
            if not run:
                raise LookupError("Live trace not found or expired.")
            if run["owner"] != user["username"]:
                raise PermissionError("This live trace belongs to another account.")
            return deepcopy(
                {k: v for k, v in run.items() if k not in {"owner", "claimed"}}
            )

    def claim(self, run_id, user, operation):
        with self.lock:
            self.read(run_id, user)
            run = self.runs[run_id]
            if run["operation"] != operation or run["claimed"]:
                raise ValueError(
                    "Live trace was already used or belongs to another operation."
                )
            run["claimed"] = True

    def emit(self, run_id, stage, state, message):
        with self.lock:
            run = self.runs.get(run_id)
            if not run or len(run["events"]) >= 100:
                return
            run["events"].append(
                {
                    "seq": len(run["events"]),
                    "stage": stage,
                    "state": state,
                    "message": message,
                    "elapsed_ms": round((time.time() - run["started_at"]) * 1000, 2),
                }
            )
            if stage == "run" and state in {"complete", "error"}:
                run["complete"] = True


JOURNAL = RunJournal()


def emit(stage, state, message):
    run_id = _current.get()
    if run_id:
        JOURNAL.emit(run_id, stage, state, message)


@contextmanager
def trace(run_id, user, operation):
    if not run_id:
        yield
        return
    JOURNAL.claim(run_id, user, operation)
    token = _current.set(run_id)
    try:
        emit(
            "identity",
            "complete",
            "Authenticated session and server-side role verified.",
        )
        yield
        emit(
            "run",
            "complete",
            "Request finished. Inspect its result and execution receipt.",
        )
    except Exception:
        emit(
            "run",
            "error",
            "Request failed. No success is inferred; inspect the response.",
        )
        raise
    finally:
        _current.reset(token)

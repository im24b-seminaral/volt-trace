"""
progress.py - Fortschritts-Events für lang laufende CLI-Kommandos.

Die Events gehen als JSON-Zeilen auf stderr, weil stdout dem Ergebnis gehört.
Ohne VOLT_TRACE_PROGRESS=1 ist alles still, damit sich das CLI für Tests und
manuelle Aufrufe unverändert verhält.
"""

import json
import os
import sys
import time


class Progress:
    def __init__(self, enabled: bool | None = None, sink=None):
        self.enabled = os.environ.get("VOLT_TRACE_PROGRESS") == "1" if enabled is None else enabled
        self.sink = sink
        self._last = 0.0

    def send(self, step: str, done: int | None = None, total: int | None = None) -> None:
        """Drosselt Zwischenstände auf 100 ms; der Endstand kommt immer durch."""
        now = time.monotonic()
        if done is not None and done != total and now - self._last < 0.1 and not self.sink:
            return
        event = {"step": step} if done is None else {"step": step, "done": done, "total": total}
        if self.sink:
            self.sink(event)
            self._last = now
            return
        if not self.enabled:
            return
        sys.stderr.write(f"@progress {json.dumps(event)}\n")
        sys.stderr.flush()
        self._last = now

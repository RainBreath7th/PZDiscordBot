from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class HealthState:
    def __init__(self, path: Path, *, reset: bool = False) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if reset or not self.path.exists():
            self.write(restarting_until=0.0)

    def write(self, *, restarting_until: float) -> None:
        payload = {
            "restarting_until": restarting_until,
            "updated_at": time.time(),
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(self.path)

    def read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def restarting_until(self) -> float:
        raw = self.read().get("restarting_until", 0)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def in_restarting_window(self, now: float | None = None) -> bool:
        clock = time.time() if now is None else now
        return self.restarting_until() > clock


def rcon_probe(host: str, port: int, password: str, timeout: float) -> bool:
    try:
        from rcon.source import Client
    except ImportError:
        log.error("rcon package missing in health probe")
        return False
    try:
        with Client(host, port, passwd=password, timeout=timeout) as client:
            client.run("players")
        return True
    except Exception:
        return False


def main() -> int:
    from bot.settings import ConfigError, Settings

    try:
        settings = Settings.from_env()
    except ConfigError:
        return 1
    state = HealthState(settings.health_state_path, reset=False)
    if state.in_restarting_window():
        return 0
    ok = rcon_probe(
        settings.rcon_host,
        settings.rcon_port,
        settings.rcon_password,
        settings.rcon_timeout,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

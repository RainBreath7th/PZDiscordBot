from __future__ import annotations

import time
from pathlib import Path

from bot.health import HealthState


def test_health_state_window(tmp_path: Path) -> None:
    path = tmp_path / "health.json"
    writer = HealthState(path, reset=True)
    writer.write(restarting_until=time.time() + 30)
    reader = HealthState(path, reset=False)
    assert reader.in_restarting_window()
    writer.write(restarting_until=time.time() - 1)
    assert not reader.in_restarting_window()

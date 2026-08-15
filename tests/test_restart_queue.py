from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from bot.rcon_client import PlayerList, RconError
from bot.restart_queue import CancelReason, QueueState, RestartQueue
from tests.conftest import make_settings


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeSleep:
    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock

    async def __call__(self, seconds: float) -> None:
        self.clock.advance(seconds)
        await asyncio.sleep(0)


class FakeRcon:
    def __init__(self) -> None:
        self.counts: list[int] = []
        self.saved = 0
        self.quits = 0
        self.fail_players = 0
        self.fail_save = False
        self.player_calls = 0

    async def players(self) -> PlayerList:
        self.player_calls += 1
        if self.fail_players > 0:
            self.fail_players -= 1
            raise RconError("down")
        count = self.counts.pop(0) if self.counts else 0
        names = tuple(f"p{i}" for i in range(count))
        return PlayerList(count=count, names=names)

    async def save(self) -> str:
        if self.fail_save:
            raise RconError("save failed")
        self.saved += 1
        return "ok"

    async def quit(self) -> str:
        self.quits += 1
        return "ok"


async def _wait_until(predicate, timeout: float = 1.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition not met")


@pytest.fixture
def harness(tmp_path: Path):
    clock = FakeClock()
    rcon = FakeRcon()
    notes: list[tuple[int, str]] = []
    windows: list[float] = []

    async def announce(_key: str) -> None:
        return None

    async def notify(user_id: int, key: str, _kwargs: dict[str, object]) -> None:
        notes.append((user_id, key))

    queue = RestartQueue(
        make_settings(health_state_path=tmp_path / "h.json"),
        rcon,
        announce=announce,
        notify=notify,
        on_window=windows.append,
        clock=clock,
        sleeper=FakeSleep(clock),
    )
    return queue, rcon, clock, notes, windows


@pytest.mark.asyncio
async def test_enqueue_rejects_second_and_timeout(harness) -> None:
    queue, rcon, clock, notes, _windows = harness
    rcon.counts = [1, 1, 1, 1, 1, 1, 1, 1]
    assert await queue.enqueue(7, "Ada") is None
    second = await queue.enqueue(8, "Bob")
    assert second is not None
    assert second.owner_id == 7
    await _wait_until(lambda: queue.snapshot().state is QueueState.IDLE)
    assert any(key == "restart.timeout" for _user, key in notes)
    assert rcon.quits == 0


@pytest.mark.asyncio
async def test_double_zero_executes_and_single_zero_does_not(harness) -> None:
    queue, rcon, _clock, notes, windows = harness
    rcon.counts = [0, 1, 0, 0]
    await queue.enqueue(7, "Ada")
    await _wait_until(lambda: rcon.quits == 1)
    assert rcon.saved == 1
    assert rcon.player_calls >= 4
    assert windows and windows[0] > 0
    assert any(key == "restart.executed" for _user, key in notes)


@pytest.mark.asyncio
async def test_now_preempts_queue(harness) -> None:
    queue, rcon, _clock, notes, _windows = harness
    rcon.counts = [2, 2, 2, 2]
    await queue.enqueue(7, "Ada")
    reason = await queue.force_now(9, "Owner")
    assert reason is None
    assert rcon.saved == 1
    assert rcon.quits == 1
    assert any(key == "restart.preempted" for _user, key in notes)


@pytest.mark.asyncio
async def test_save_failure_does_not_quit(harness) -> None:
    queue, rcon, _clock, _notes, _windows = harness
    rcon.fail_save = True
    reason = await queue.force_now(1, "Owner")
    assert reason is CancelReason.SAVE_FAILED
    assert rcon.quits == 0
    assert queue.snapshot().state is QueueState.IDLE


@pytest.mark.asyncio
async def test_consecutive_rcon_failures_cancel_queue(harness) -> None:
    queue, rcon, _clock, notes, _windows = harness
    rcon.fail_players = 5
    rcon.counts = [1]
    await queue.enqueue(7, "Ada")
    await _wait_until(lambda: queue.snapshot().state is QueueState.IDLE)
    assert rcon.quits == 0
    assert any(key == "restart.rcon_failed_cancel" for _user, key in notes)


@pytest.mark.asyncio
async def test_cancel_own_and_status_window(harness) -> None:
    queue, rcon, _clock, _notes, _windows = harness
    rcon.counts = [3, 3, 3, 3]
    await queue.enqueue(7, "Ada")
    ok, _snap = await queue.cancel(8, as_admin=False)
    assert ok is False
    ok, _snap = await queue.cancel(7, as_admin=False)
    assert ok is True
    assert queue.snapshot().state is QueueState.IDLE
    await queue.force_now(1, "Owner")
    assert rcon.quits == 1
    assert any(until > 0 for until in _windows)

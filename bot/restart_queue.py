from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from bot.rcon_client import RconError
from bot.settings import Settings

log = logging.getLogger(__name__)


class QueueState(str, Enum):
    IDLE = "idle"
    QUEUED = "queued"
    RESTARTING = "restarting"


class CancelReason(str, Enum):
    USER = "user"
    TIMEOUT = "timeout"
    RCON_FAILED = "rcon_failed"
    PREEMPTED = "preempted"
    SAVE_FAILED = "save_failed"
    QUIT_FAILED = "quit_failed"


class Clock(Protocol):
    def __call__(self) -> float: ...


class Sleeper(Protocol):
    async def __call__(self, seconds: float) -> None: ...


@dataclass(frozen=True)
class QueueSnapshot:
    state: QueueState
    owner_id: int | None = None
    owner_name: str | None = None
    started_at: float | None = None
    deadline_at: float | None = None
    restarting_until: float | None = None
    last_reason: CancelReason | None = None

    def elapsed(self, now: float) -> int:
        if self.started_at is None:
            return 0
        return max(0, int(now - self.started_at))

    def remaining(self, now: float) -> int:
        if self.deadline_at is None:
            return 0
        return max(0, int(self.deadline_at - now))

    def grace_remaining(self, now: float) -> int:
        if self.restarting_until is None:
            return 0
        return max(0, int(self.restarting_until - now))


Notify = Callable[[int, str, dict[str, object]], Awaitable[None]]
Announce = Callable[[str], Awaitable[None]]


class RestartQueue:
    def __init__(
        self,
        settings: Settings,
        rcon: object,
        *,
        announce: Announce,
        notify: Notify,
        on_window: Callable[[float], None],
        clock: Clock | None = None,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._settings = settings
        self._rcon = rcon
        self._announce = announce
        self._notify = notify
        self._on_window = on_window
        self._clock = clock or time.time
        self._sleep = sleeper or asyncio.sleep
        self._lock = asyncio.Lock()
        self._state = QueueState.IDLE
        self._owner_id: int | None = None
        self._owner_name: str | None = None
        self._started_at: float | None = None
        self._deadline_at: float | None = None
        self._restarting_until: float | None = None
        self._last_reason: CancelReason | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._executing = False

    def now(self) -> float:
        return self._clock()

    def snapshot(self) -> QueueSnapshot:
        return QueueSnapshot(
            state=self._state,
            owner_id=self._owner_id,
            owner_name=self._owner_name,
            started_at=self._started_at,
            deadline_at=self._deadline_at,
            restarting_until=self._restarting_until,
            last_reason=self._last_reason,
        )

    def in_restarting_window(self) -> bool:
        if self._state != QueueState.RESTARTING or self._restarting_until is None:
            return False
        return self._clock() < self._restarting_until

    async def enqueue(self, owner_id: int, owner_name: str) -> QueueSnapshot | None:
        async with self._lock:
            if self._state != QueueState.IDLE:
                return self.snapshot()
            now = self._clock()
            self._state = QueueState.QUEUED
            self._owner_id = owner_id
            self._owner_name = owner_name
            self._started_at = now
            self._deadline_at = now + self._settings.restart_timeout
            self._last_reason = None
            self._stop = asyncio.Event()
            self._task = asyncio.create_task(self._run_queue(), name="restart-queue")
            log.info(
                "restart queued",
                extra={"operator": owner_id, "queue_state": self._state.value},
            )
            return None

    async def cancel(self, actor_id: int, *, as_admin: bool) -> tuple[bool, QueueSnapshot]:
        async with self._lock:
            snap = self.snapshot()
            if self._state != QueueState.QUEUED or self._owner_id is None:
                return False, snap
            if not as_admin and actor_id != self._owner_id:
                return False, snap
            owner_id = self._owner_id
            self._last_reason = CancelReason.USER
            self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        await self._clear(CancelReason.USER)
        return True, QueueSnapshot(
            state=QueueState.IDLE,
            owner_id=owner_id,
            owner_name=snap.owner_name,
            last_reason=CancelReason.USER,
        )

    async def force_now(self, actor_id: int, actor_name: str) -> CancelReason | None | str:
        preempted_owner: int | None = None
        async with self._lock:
            if self._state == QueueState.RESTARTING and self.in_restarting_window():
                return "already_restarting"
            if self._state == QueueState.QUEUED and self._owner_id is not None:
                preempted_owner = self._owner_id
                self._last_reason = CancelReason.PREEMPTED
                self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        if self._state == QueueState.RESTARTING or self.in_restarting_window():
            return None
        if preempted_owner is not None:
            await self._safe_notify(preempted_owner, "restart.preempted", {})
        await self._clear(CancelReason.PREEMPTED)
        reason = await self._execute(skip_empty_check=True)
        log.info(
            "forced restart",
            extra={"operator": actor_id, "queue_state": self._state.value},
        )
        _ = actor_name
        return reason

    async def _run_queue(self) -> None:
        failures = 0
        owner_id = self._owner_id or 0
        try:
            while not self._stop.is_set():
                now = self._clock()
                if self._deadline_at is not None and now >= self._deadline_at:
                    await self._clear(CancelReason.TIMEOUT)
                    await self._safe_notify(owner_id, "restart.timeout", {})
                    return
                try:
                    listing = await self._rcon.players()  # type: ignore[attr-defined]
                    failures = 0
                except RconError:
                    failures += 1
                    if failures >= self._settings.rcon_fail_threshold:
                        await self._clear(CancelReason.RCON_FAILED)
                        await self._safe_notify(owner_id, "restart.rcon_failed_cancel", {})
                        return
                    await self._sleep(self._settings.poll_interval)
                    continue
                if listing.count == 0 and not listing.names:
                    await self._sleep(self._settings.empty_confirm_seconds)
                    try:
                        again = await self._rcon.players()  # type: ignore[attr-defined]
                    except RconError:
                        failures += 1
                        await self._sleep(self._settings.poll_interval)
                        continue
                    if again.count == 0 and not again.names:
                        reason = await self._execute(skip_empty_check=True)
                        if reason is None:
                            await self._safe_notify(owner_id, "restart.executed", {})
                        elif reason == CancelReason.SAVE_FAILED:
                            await self._safe_notify(
                                owner_id, "restart.save_failed", {"detail": "save"}
                            )
                        elif reason == CancelReason.QUIT_FAILED:
                            await self._safe_notify(
                                owner_id, "restart.quit_failed", {"detail": "quit"}
                            )
                        return
                await self._sleep(self._settings.poll_interval)
        except asyncio.CancelledError:
            return

    async def _execute(self, *, skip_empty_check: bool) -> CancelReason | None:
        _ = skip_empty_check
        async with self._lock:
            if self._executing or (
                self._state == QueueState.RESTARTING and self.in_restarting_window()
            ):
                return None
            self._executing = True
        quit_sent = False
        try:
            try:
                await self._announce("restart.executing_ingame")
            except RconError as exc:
                log.warning("pre-restart announce failed", extra={"detail": str(exc)})
            try:
                await self._rcon.save()  # type: ignore[attr-defined]
            except RconError as exc:
                await self._clear(CancelReason.SAVE_FAILED)
                log.error("save failed", extra={"detail": str(exc)})
                return CancelReason.SAVE_FAILED
            try:
                await self._rcon.quit()  # type: ignore[attr-defined]
                quit_sent = True
            except RconError as exc:
                # quit often dies because the process is already exiting
                log.info("quit returned error", extra={"detail": str(exc)})
                quit_sent = True
            except asyncio.CancelledError:
                if not quit_sent:
                    raise
            until = self._clock() + self._settings.restart_grace
            async with self._lock:
                self._state = QueueState.RESTARTING
                self._restarting_until = until
                self._owner_id = None
                self._owner_name = None
                self._started_at = None
                self._deadline_at = None
                self._task = None
            self._on_window(until)
            asyncio.create_task(self._expire_window(until), name="restart-window")
            return None
        finally:
            self._executing = False

    async def _expire_window(self, until: float) -> None:
        delay = max(0.0, until - self._clock())
        await self._sleep(delay)
        async with self._lock:
            if self._state == QueueState.RESTARTING and self._restarting_until == until:
                self._state = QueueState.IDLE
                self._restarting_until = None
                self._on_window(0.0)

    async def _clear(self, reason: CancelReason) -> None:
        async with self._lock:
            self._state = QueueState.IDLE
            self._owner_id = None
            self._owner_name = None
            self._started_at = None
            self._deadline_at = None
            self._last_reason = reason
            self._task = None
            if reason != CancelReason.PREEMPTED:
                self._stop = asyncio.Event()

    async def _safe_notify(self, user_id: int, key: str, kwargs: dict[str, object]) -> None:
        try:
            await self._notify(user_id, key, kwargs)
        except Exception:
            log.exception("notify failed", extra={"operator": user_id, "detail": key})

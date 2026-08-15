from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from bot.constants import (
    DEFAULT_MIN_TIER,
    SUPPORTED_LOCALES,
    Tier,
)
from bot.settings import ConfigError

log = logging.getLogger(__name__)


def _as_id_list(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ConfigError(f"{field_name} must be a list")
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            continue
        if not text.isdigit():
            raise ConfigError(f"{field_name} entries must be numeric snowflakes")
        out.append(text)
    return tuple(out)


def _dig(data: Any, dotted: str) -> Any:
    current = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted)
        current = current[part]
    return current


@dataclass(frozen=True)
class GuildPermissions:
    guild_id: str
    admin_role_ids: frozenset[str]
    member_role_ids: frozenset[str]
    command_channel_ids: frozenset[str]
    break_glass_user_ids: frozenset[str]
    command_min_tier: dict[str, Tier]


@dataclass(frozen=True)
class PermissionsFile:
    guilds: dict[str, GuildPermissions]

    def guild_ids(self) -> tuple[str, ...]:
        return tuple(self.guilds.keys())

    def get(self, guild_id: int | str) -> GuildPermissions | None:
        return self.guilds.get(str(guild_id))


@dataclass(frozen=True)
class I18nFile:
    discord_locales: tuple[str, ...]
    game_locales: tuple[str, ...]


@dataclass(frozen=True)
class RangeLimit:
    minimum: int
    maximum: int

    def contains(self, value: int) -> bool:
        return self.minimum <= value <= self.maximum


@dataclass(frozen=True)
class LimitsFile:
    item_count: RangeLimit
    xp: RangeLimit
    vehicle: int
    horde: RangeLimit
    servermsg_max_chars: int
    confirm_timeout_seconds: int


@dataclass
class LoadedYaml:
    permissions: PermissionsFile
    i18n: I18nFile
    limits: LimitsFile
    locales: dict[str, dict[str, Any]]
    mtimes: dict[str, float] = field(default_factory=dict)


def _parse_permissions(raw: Any) -> PermissionsFile:
    if not isinstance(raw, dict) or "guilds" not in raw:
        raise ConfigError("permissions.yaml must contain a guilds mapping")
    guilds_raw = raw["guilds"]
    if not isinstance(guilds_raw, dict) or not guilds_raw:
        raise ConfigError("permissions.yaml guilds must be a non-empty mapping")
    guilds: dict[str, GuildPermissions] = {}
    for guild_id, body in guilds_raw.items():
        gid = str(guild_id).strip()
        if not gid.isdigit():
            raise ConfigError(f"guild id {gid!r} must be a numeric snowflake")
        if not isinstance(body, dict):
            raise ConfigError(f"guild {gid} must be a mapping")
        overrides_raw = body.get("command_min_tier") or {}
        if not isinstance(overrides_raw, dict):
            raise ConfigError(f"guild {gid} command_min_tier must be a mapping")
        overrides: dict[str, Tier] = {}
        for key, value in overrides_raw.items():
            try:
                overrides[str(key)] = Tier[str(value).strip().upper()]
            except KeyError as exc:
                raise ConfigError(
                    f"guild {gid} command_min_tier.{key} must be A, B, or C"
                ) from exc
            if str(key) not in DEFAULT_MIN_TIER:
                raise ConfigError(f"guild {gid} unknown command key {key!r}")
        guilds[gid] = GuildPermissions(
            guild_id=gid,
            admin_role_ids=frozenset(_as_id_list(body.get("admin_role_ids"), "admin_role_ids")),
            member_role_ids=frozenset(
                _as_id_list(body.get("member_role_ids"), "member_role_ids")
            ),
            command_channel_ids=frozenset(
                _as_id_list(body.get("command_channel_ids"), "command_channel_ids")
            ),
            break_glass_user_ids=frozenset(
                _as_id_list(body.get("break_glass_user_ids"), "break_glass_user_ids")
            ),
            command_min_tier=overrides,
        )
    return PermissionsFile(guilds=guilds)


def _parse_locales_list(raw: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(raw, list) or not raw:
        raise ConfigError(f"{field_name} must be a non-empty list")
    out: list[str] = []
    for item in raw:
        locale = str(item).strip()
        if locale not in SUPPORTED_LOCALES:
            raise ConfigError(f"{field_name} contains unsupported locale {locale!r}")
        if locale not in out:
            out.append(locale)
    return tuple(out)


def _parse_i18n(raw: Any) -> I18nFile:
    if not isinstance(raw, dict):
        raise ConfigError("i18n.yaml must be a mapping")
    return I18nFile(
        discord_locales=_parse_locales_list(raw.get("discord_locales"), "discord_locales"),
        game_locales=_parse_locales_list(raw.get("game_locales"), "game_locales"),
    )


def _parse_range(raw: Any, field_name: str) -> RangeLimit:
    if not isinstance(raw, dict) or "min" not in raw or "max" not in raw:
        raise ConfigError(f"{field_name} must have min and max")
    try:
        minimum = int(raw["min"])
        maximum = int(raw["max"])
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} min/max must be integers") from exc
    if minimum > maximum:
        raise ConfigError(f"{field_name} min cannot exceed max")
    return RangeLimit(minimum=minimum, maximum=maximum)


def _parse_limits(raw: Any) -> LimitsFile:
    if not isinstance(raw, dict):
        raise ConfigError("limits.yaml must be a mapping")
    try:
        vehicle = int(raw.get("vehicle", 1))
        servermsg_max = int(raw.get("servermsg_max_chars", 200))
        confirm_timeout = int(raw.get("confirm_timeout_seconds", 30))
    except (TypeError, ValueError) as exc:
        raise ConfigError("limits.yaml numeric fields are invalid") from exc
    if vehicle < 1 or servermsg_max < 1 or confirm_timeout < 1:
        raise ConfigError("limits.yaml numeric fields must be >= 1")
    return LimitsFile(
        item_count=_parse_range(raw.get("item_count"), "item_count"),
        xp=_parse_range(raw.get("xp"), "xp"),
        vehicle=vehicle,
        horde=_parse_range(raw.get("horde"), "horde"),
        servermsg_max_chars=servermsg_max,
        confirm_timeout_seconds=confirm_timeout,
    )


def _load_yaml(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc


def _bundled_config_dir() -> Path | None:
    for candidate in (
        Path("/app/config.defaults"),
        Path(__file__).resolve().parents[1] / "config.defaults",
        Path(__file__).resolve().parents[1] / "config",
    ):
        if candidate.is_dir():
            return candidate
    return None


def _resolve_config_file(config_dir: Path, relative: str) -> tuple[Any, Path]:
    primary = config_dir / relative
    if primary.is_file():
        return _load_yaml(primary), primary
    bundled = _bundled_config_dir()
    if bundled is not None:
        fallback = bundled / relative
        if fallback.is_file():
            log.warning("config file %s missing, falling back to %s", primary, fallback)
            return _load_yaml(fallback), fallback
    raise ConfigError(f"missing config file: {primary}")


def load_yaml_bundle(config_dir: Path) -> LoadedYaml:
    if not config_dir.is_dir():
        raise ConfigError(f"CONFIG_DIR does not exist: {config_dir}")
    # Resolve each required file individually so a sparse bind-mount
    # (e.g. host ./config only contains permissions.yaml) still boots
    # by falling back to the baked-in defaults for the rest.
    perm_data, perm_path = _resolve_config_file(config_dir, "permissions.yaml")
    i18n_data, i18n_path = _resolve_config_file(config_dir, "i18n.yaml")
    limits_data, limits_path = _resolve_config_file(config_dir, "limits.yaml")

    locales: dict[str, dict[str, Any]] = {}
    locale_paths: dict[str, Path] = {}
    for locale in SUPPORTED_LOCALES:
        rel = f"locales/{locale}.yaml"
        data, resolved = _resolve_config_file(config_dir, rel)
        if not isinstance(data, dict):
            raise ConfigError(f"{resolved} must be a mapping")
        locales[locale] = data
        locale_paths[locale] = resolved

    paths = {"permissions": perm_path, "i18n": i18n_path, "limits": limits_path}
    mtimes = {
        str(path): path.stat().st_mtime
        for path in [*paths.values(), *locale_paths.values()]
    }
    return LoadedYaml(
        permissions=_parse_permissions(perm_data),
        i18n=_parse_i18n(i18n_data),
        limits=_parse_limits(limits_data),
        locales=locales,
        mtimes=mtimes,
    )


class ConfigStore:
    """Last-good YAML bundle with mtime hot reload."""

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self._loaded = load_yaml_bundle(config_dir)

    @property
    def permissions(self) -> PermissionsFile:
        return self._loaded.permissions

    @property
    def i18n(self) -> I18nFile:
        return self._loaded.i18n

    @property
    def limits(self) -> LimitsFile:
        return self._loaded.limits

    @property
    def locales(self) -> dict[str, dict[str, Any]]:
        return self._loaded.locales

    def lookup(self, locale: str, key: str) -> str:
        for candidate in (locale, "en"):
            pack = self._loaded.locales.get(candidate)
            if not pack:
                continue
            try:
                value = _dig(pack, key)
            except KeyError:
                continue
            if isinstance(value, str):
                return value
        return key

    def reload_if_changed(self) -> bool:
        changed = False
        for path_str, known in self._loaded.mtimes.items():
            path = Path(path_str)
            try:
                current = path.stat().st_mtime
            except OSError:
                log.error("config file disappeared", extra={"detail": path_str})
                return False
            if current != known:
                changed = True
                break
        if not changed:
            return False
        try:
            self._loaded = load_yaml_bundle(self.config_dir)
        except ConfigError:
            log.exception("hot reload failed; keeping last-good config")
            return False
        log.info("config hot-reloaded")
        return True

    def syncable_guild_ids(self) -> list[int]:
        ids: list[int] = []
        for raw in self.permissions.guild_ids():
            value = int(raw)
            if value == 0:
                continue
            ids.append(value)
        return ids

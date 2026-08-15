# PZ Discord Bot

A Discord bot that manages one Project Zomboid dedicated server through semantic slash commands and Source RCON.

This context is a glossary. Implementation lives in `bot/` and `docs` stay out of this file.

## Language

**Tier**:
A Discord-side permission band. A is the owner-role set, B is the PZ-member-role set, C is everyone else. A member's effective Tier is the highest band among the roles they hold.
_Avoid_: admin, member, everyone

**RestartQueue**:
The single in-process queued restart. The requester is identified by Discord user id. It is not persisted.
_Avoid_: job, task, schedule

**RestartingWindow**:
The grace period after `save` and `quit` have been sent, during which RCON is expected to be unreachable.
_Avoid_: cooldown, downtime

**BreakGlass**:
The per-guild list of Discord user ids allowed to change a player who is already in-game admin.
_Avoid_: superadmin, owner

**GameLocale**:
A locale used for sequential in-game `servermsg` lines.
_Avoid_: language, lang

**DiscordLocale**:
A locale used as one section of a Discord embed reply.
_Avoid_: language, lang

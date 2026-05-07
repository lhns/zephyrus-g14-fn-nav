# 6. Fn+Up/Down emits PgUp/PgDn + restores brightness; Ctrl+Fn+Up/Down is the only intentional brightness control

Date: 2026-05-07

## Status

Accepted.

## Context

On the GA401L, Fn+Up and Fn+Down are also wired to keyboard-backlight
brightness adjustment. Stage 1 diagnostic confirmed the EC firmware adjusts
brightness *before* the corresponding `0xC4` / `0xC5` HID report reaches
user-mode. We cannot suppress the brightness change from a Windows app —
it has already happened by the time we observe the event.

This creates a conflict with the goal of using Fn+Up/Down for PgUp/PgDn:

- If we naïvely emit PgUp/PgDn on `0xC4`/`0xC5`, every press also flickers
  the keyboard backlight one step away from where it was — annoying.
- If we drop the mapping, PgUp/PgDn has to come from somewhere else
  (Alt+Fn+arrow, Ctrl+Fn+arrow, a non-Fn modifier) — every alternative
  costs the user a different shortcut, or adds new infrastructure
  (Windows-level keyboard hook).

Alternatives considered:

| Option | Pro | Con |
| --- | --- | --- |
| Drop PgUp/PgDn entirely | simplest | user loses the feature |
| Alt+Fn+Left/Right → PgUp/PgDn | keeps Ctrl+Home/End | loses Alt+Home, redirects user away from arrow-up/down ergonomics |
| Ctrl+Fn+Left/Right → PgUp/PgDn | matches user's first-instinct suggestion | loses Ctrl+Home/Ctrl+End (programmer-relevant) |
| Keep Fn+Up/Down → PgUp/PgDn, restore brightness afterwards | preserves the intuitive mapping; preserves Ctrl+Home/End | brief brightness flicker; have to also reclaim Ctrl+Fn+Up/Down for actual brightness adjustment |

## Decision

Take the last option. Specifically:

- **Plain Fn+Up/Down** → emit `VK_PRIOR` / `VK_NEXT`, then write a
  brightness command back to the keyboard restoring `target_brightness` to
  whatever the user last set via Ctrl+Fn+Up/Down.
- **Ctrl+Fn+Up/Down** → do *not* emit PgUp/PgDn. Update
  `target_brightness` in process state. The EC has already physically
  adjusted brightness; we just record the new level.
- Modifier passthrough for Shift / Alt / Win remains intact: Shift+Fn+Up
  → Shift held + emit `VK_PRIOR` → Windows interprets as Shift+PgUp.

Brightness control is now reachable *only* via Ctrl+Fn+Up/Down. Direct
Fn+Up/Down without modifier is reserved for paging.

## Consequences

- Visible brightness flicker (~tens of ms) on every PgUp/PgDn via this
  path. Acceptable per user.
- Ctrl+Home / Ctrl+End remain available (jump-to-top/bottom of document)
  via Ctrl+Fn+Left/Right passthrough — these are valuable for programming
  and would have been lost in the rejected Ctrl+Fn-arrow alternative.
- Ctrl+Fn+Up/Down loses any *other* meaning. Acceptable in v1 — no
  prior shortcut was bound there.
- If the brightness flicker turns out to be too jarring in real use, the
  fallback is to switch to "drop PgUp/PgDn" or "Alt+Fn+Left/Right" — both
  are local code changes in `src/main.rs::run`'s match block.

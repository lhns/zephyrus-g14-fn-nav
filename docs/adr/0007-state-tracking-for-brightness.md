# 7. Track keyboard brightness as in-process state, not by reading from hardware

Date: 2026-05-07

## Status

Accepted.

## Context

ADR 0006 commits us to restoring brightness after Fn+Up/Down. To restore,
we need a "target brightness" value. Two ways to obtain it:

1. **Read** current brightness from the keyboard via HID, refreshed on
   every event so external changes (Armoury Crate, sleep/wake) don't
   cause us to overwrite the user's intent.
2. **Track** brightness as in-process state, anchored at startup.

Investigation: G-Helper's `app/USB/Aura.cs` (`DirectBrightness`) only
*writes* brightness via the byte sequence `[0x5A, 0xBA, 0xC5, 0xC4, level]`.
There is no public reverse-engineered read path; G-Helper itself stores
brightness as application state. We could optionally probe with
`HidDevice::get_feature_report(0x5A, …)` at startup to see if the device
returns a parseable value, but assuming a reliable read path exists is not
warranted by the available evidence.

## Decision

Maintain `target_brightness: u8` (range 0..=3) in process state.

- **Default at startup:** `target_brightness = 0` (off); **no** brightness
  command is written. The user's existing level is preserved. The default
  matches the typical post-boot state of the GA401L — backlight off — so
  in the common case (launching just after login) `target == actual` and
  the first plain Fn+Up/Down restores invisibly. If actual differs, that
  first press will snap brightness to `0` (one visible step), after which
  `target == actual`. Forcing a non-zero level on startup was rejected
  because it changed brightness on every launch — an explicit user
  complaint.
- **On Ctrl+Fn+Up:** `target_brightness = (target_brightness + 1).min(3)`.
  The EC has already bumped; we only update the tracker.
- **On Ctrl+Fn+Down:** `target_brightness = target_brightness.saturating_sub(1)`.
- **On plain Fn+Up/Down:** after emitting PgUp/PgDn, write
  `target_brightness` back to the keyboard.

A get-feature read may be added later as an optional self-correction step
if the protocol turns out to support it; this ADR does not block that.

## Consequences

- External brightness changes (Armoury Crate, G-Helper, sleep/wake)
  invalidate `target_brightness` until the user next does Ctrl+Fn+Up or
  Ctrl+Fn+Down to re-anchor. In the steady state this is invisible; the
  drift only shows up the next time a plain Fn+Up/Down restore writes the
  stale tracker value back. Acceptable.
- The startup write (`level=2`) is mildly opinionated — it changes
  brightness for the user the first time the listener launches. If level
  2 is the wrong default for them, ADR 0004 (no config file in v1)
  applies; revisit if it bites.
- No risk of an incorrect read corrupting the tracker, since we don't read.
- Saturation at 0 and 3 is enforced in our tracker, matching what we
  believe the EC does; if the EC's behaviour differs the worst case is a
  one-step off-by-one, self-correcting on next Ctrl+Fn+Up/Down.

# 1. Listen via the ASUS HID interface instead of a Windows keyboard hook

Date: 2026-05-07

## Status

Accepted.

## Context

The user wants `Fn+Left → Home` and `Fn+Right → End` on a Zephyrus G14
GA401L. Several Windows-level approaches exist for keyboard remapping —
AutoHotkey, PowerToys Keyboard Manager, low-level keyboard hooks
(`SetWindowsHookExW(WH_KEYBOARD_LL, …)`), Interception driver, scancode-map
in the registry. None of them can see the Fn key on this laptop because the
Embedded Controller (EC) firmware processes Fn before any signal reaches the
Windows input stack. This is consistent with what the G-Helper maintainer
documented and what the Cursor Control / G14Manager projects observed.

Stage 1 diagnostic confirmed, however, that the EC *does* emit a
vendor-specific HID code on a separate ASUS HID collection
(`mi_02&col01`, report `0x5A`) for Fn+arrow. The combo is observable, just
not via the standard keyboard input stream.

## Decision

The listener attaches directly to the ASUS HID collection via the `hidapi`
crate, watches for the four action codes (`0xB2 / 0xB3 / 0xC4 / 0xC5`), and
synthesises the corresponding navigation key via `SendInput`. **The same
HID handle is also used to write keyboard-brightness output reports** —
the listener is bidirectional on this interface (see ADR 0006/0007).

## Consequences

- We bypass the entire Windows keyboard pipeline for navigation input. The
  output side still uses `SendInput` for navigation keys so all downstream
  apps (editors, browsers, terminals) see the synthetic Home/End/PgUp/PgDn
  through the normal Windows input stack.
- The HID handle is used in both directions: read for vendor action codes,
  write for `[0x5A, 0xBA, 0xC5, 0xC4, level]` brightness commands. One
  device open per listener instance is sufficient.
- No driver, no service, no kernel-mode component required.
- Solution is laptop-specific. Codes captured here apply to *this* GA401L;
  another ASUS model would need to re-run the diagnostic.
- We coexist with Armoury Crate / G-Helper / ASUS Optimization service
  because HID opens with `FILE_SHARE_READ | FILE_SHARE_WRITE`. Multiple
  consumers sharing the same HID collection is supported by Windows.

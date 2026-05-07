# 3. Synthesise navigation keys with `SendInput` + `KEYEVENTF_EXTENDEDKEY`

Date: 2026-05-07

## Status

Accepted.

## Context

Once the listener has decoded a Fn+arrow event, it must inject the
corresponding navigation key (Home / End / Page Up / Page Down) into the
Windows input stream. Two main techniques are available:

1. **Virtual-key injection** — `SendInput` with a `VIRTUAL_KEY` and
   `wScan = 0`. Windows looks up the active layout to determine what
   scancode to deliver.
2. **Scancode injection** — `SendInput` with `KEYEVENTF_SCANCODE` and the
   physical scancode. Bypasses layout translation; reaches DirectInput
   apps that ignore virtual-key injection.

Home / End / Page Up / Page Down are *extended* keys — their physical
scancodes have the legacy 0xE0 prefix on the IBM-PC scan set. Without the
`KEYEVENTF_EXTENDEDKEY` flag, some applications (notably console hosts
and a handful of legacy editors) will misinterpret the synthesised key as
its non-extended sibling, e.g. End vs. numpad-1.

## Decision

Use virtual-key injection (`wVk` set, `wScan` = 0) **with**
`KEYEVENTF_EXTENDEDKEY` set on both the down and up `INPUT` records.

```rust
KEYBDINPUT { wVk: VK_HOME, wScan: 0,
             dwFlags: KEYEVENTF_EXTENDEDKEY, … }
KEYBDINPUT { wVk: VK_HOME, wScan: 0,
             dwFlags: KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, … }
```

Modifier passthrough is left to the Windows input stack — when the user
holds Shift or Ctrl alongside Fn+arrow, those modifiers are already "down"
in Windows' state (they reach Windows as normal HID keyboard reports), so
the synthesised VK naturally becomes Shift+End / Ctrl+Home / etc.

## Consequences

- Works in every standard Windows app (Win32, UWP, WPF, Electron, browsers,
  Office, IDEs).
- **Known limitation:** some DirectInput-only apps (a few games, RDP
  clients in certain modes) do not see virtual-key injection. If a target
  app is affected, switch to scancode injection — code change is local to
  `send_key`. Out of scope for v1.
- Modifier passthrough is automatic and requires no special handling in
  the listener.
- We do not synthesise auto-repeat ourselves. If the EC sends repeated
  HID reports while Fn+arrow is held, repeats happen for free; if not,
  this can be added later as timer-driven repeat.

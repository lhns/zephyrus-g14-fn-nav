# 5. No client-side auto-repeat in v1

Date: 2026-05-07

## Status

Accepted (revisitable).

## Context

A standard PC keyboard auto-repeats when a key is held down. Windows owns the
repeat for keys delivered via the standard input stack (initial delay +
repeat rate are configurable in the Control Panel).

Stage 1 collision-test capture observed that the GA401L EC does **not**
auto-repeat Fn+arrow. Holding Fn+Left for ~3 seconds produced exactly one
key-down vendor code (`0xB2`) and one key-up (`0x00`) on release — no
intermediate reports. So if our listener simply emits one VK on every
key-down it sees, holding Fn+arrow does *not* produce a repeating Home /
End / PgUp / PgDn from the user's perspective.

For Home and End this is fine — they are one-shot operations.
For PgUp / PgDn, users typically expect repeat for fast scrolling.

Implementing client-side repeat means: on key-down, start a timer. After an
initial delay (~250 ms, matching Windows' default), fire the synthetic VK
at a steady rate (~30 ms) until key-up arrives. Cancel the timer on key-up.

## Decision

Defer. v1 emits exactly one `SendInput` per Fn+arrow press. No repeat.

## Consequences

- Pressing-and-holding Fn+Down does *not* scroll page-by-page repeatedly.
  The user must tap repeatedly. Acceptable for the stated primary use case
  (Home/End for programming).
- If repeat is later wanted, the change is local: introduce a small state
  machine in `run()` keyed off the action_code, with a timer thread feeding
  `SendInput` while the key is held. Or use `windows::Win32::System::Threading::CreateTimerQueueTimer`.
- Decision is cheap to revisit because no API has been published yet — the
  listener is a private executable on the user's machine.
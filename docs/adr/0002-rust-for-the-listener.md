# 2. Rust for the production listener

Date: 2026-05-07

## Status

Accepted.

## Context

Two stages of work, with different requirements:

- **Stage 1 (diagnostic):** throwaway exploration. May iterate the script
  several times to interpret unknown raw bytes. Output is captured to a
  log; speed-of-iteration matters more than runtime cost.
- **Stage 2 (production listener):** runs continuously in the background
  for the lifetime of the user's login session. Footprint, startup time,
  and "does it just work" matter; iteration speed does not.

Candidates considered for Stage 2: Python (with pywinusb), C# (.NET), C++
(native Win32), AutoHotkey, Rust.

## Decision

Stage 1 stays in **Python** (already implemented at `diagnostic/hid_listener.py`).
Stage 2 uses **Rust** with `hidapi` and the `windows` crate.

## Consequences

- Single statically-linked .exe, no runtime dependency for the user. No need
  to install Python on the deploy target (even though the user has Rye
  Python installed today, that may not be true after a reformat).
- Low memory and CPU footprint suitable for a process launched at every
  login. `panic = "abort"` and `lto + opt-level = "z"` keep the release
  binary small.
- `windows` crate provides native Win32 bindings (specifically
  `Win32_UI_Input_KeyboardAndMouse` for `SendInput`).
- `hidapi` is the de-facto cross-platform HID library; the same crate is
  used by Linux/macOS port targets if the project ever needs them.
- Cost: a Rust toolchain is required to build. The user already has cargo
  installed; for distribution we ship the compiled .exe, not source.

## Rejected alternatives

- **AutoHotkey** — cannot see the ASUS HID interface; would have forced a
  substitute-modifier workaround. Already rejected at the planning stage
  in favour of a real Fn+arrow hook (see ADR 0001).
- **C# / .NET** — viable, but adds a runtime dependency or a 50+ MB AOT
  binary. Worse footprint for a daemon-style process.
- **Python frozen with PyInstaller** — same footprint problem, plus
  startup time. Already used for Stage 1 where it doesn't matter.
- **C++ with native Win32** — equally capable; passed over for
  developer-ergonomics reasons (memory safety, error handling).

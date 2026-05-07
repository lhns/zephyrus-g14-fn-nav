# zephyrus-g14-fn-nav

Native Home / End / Page Up / Page Down for the ASUS ROG Zephyrus G14
(GA401L). A small Rust daemon that hooks the Fn-arrow vendor codes at the
HID level and emits the corresponding navigation keys via `SendInput`.

## Why

The G14 keyboard has no dedicated Home, End, PgUp, or PgDn keys. The usual
Windows remapping tools — AutoHotkey, PowerToys Keyboard Manager, low-level
keyboard hooks — cannot help, because the laptop's Embedded Controller (EC)
processes the Fn key in firmware before any signal reaches Windows. From
the OS's perspective, "Fn" doesn't exist.

It turns out the EC *does* expose Fn-combo events through a separate ASUS
HID interface as vendor-specific codes. This program opens that interface
directly, watches for the four codes that correspond to Fn+arrow, and
translates them into ordinary Windows keystrokes that every app
understands.

No driver, no service, no kernel mode. Single ~180 KB binary.

## Mappings

| Combo                | Effect                                                                    |
| -------------------- | ------------------------------------------------------------------------- |
| **Fn + Left**        | Home                                                                      |
| **Fn + Right**       | End                                                                       |
| **Fn + Up**          | Page Up (keyboard backlight is restored after the EC bumps it)            |
| **Fn + Down**        | Page Down (keyboard backlight is restored)                                |
| Shift + Fn + arrow   | Shift + Home/End/PgUp/PgDn — selection works through modifier passthrough |
| Ctrl + Fn + Left     | Ctrl + Home — jump to top of document                                     |
| Ctrl + Fn + Right    | Ctrl + End — jump to bottom of document                                   |
| **Ctrl + Fn + Up**   | Increase keyboard backlight one step (no PgUp emitted)                    |
| **Ctrl + Fn + Down** | Decrease keyboard backlight one step (no PgDn emitted)                    |

The Ctrl+Fn+Up/Ctrl+Fn+Down combos are the only intentional way to adjust
backlight, since plain Fn+Up/Down is now reserved for paging. See
[`docs/adr/0006-fn-updown-pgup-and-brightness-restore.md`](docs/adr/0006-fn-updown-pgup-and-brightness-restore.md)
for the rationale.

## Hardware compatibility

Verified on the ASUS ROG Zephyrus G14 GA401L (USB VID `0x0B05`, PID
`0x1866`). Other ASUS laptops *may* work — the architecture (vendor codes
on a separate HID interface) is consistent across the line, but the
specific code values for Fn+arrow may differ. To check your model, run the
diagnostic tool below and compare against
[`docs/codes.md`](docs/codes.md).

## Build

Requires the Rust toolchain (`cargo`).

```
cargo build --release
```

Output: `target\release\zephyrus-g14-fn-nav.exe`. Single statically linked
binary, no runtime dependencies.

## Run

```
target\release\zephyrus-g14-fn-nav.exe
```

The console window prints status lines when Ctrl+Fn+Up/Down adjusts the
brightness target. Hide the window if you don't want it — Windows
Subsystem won't show one if you build with
`#![windows_subsystem = "windows"]`. Left as a console binary in v1 for
debuggability.

## Auto-start at login

Download the installer from the latest
[Release](https://github.com/lhns/zephyrus-g14-fn-nav/releases) and
double-click. It's a single self-extracting `.bat` (~250 KB) with the
binary embedded — no separate `.exe` to place.

The installer offers three modes:

| # | Mode                                          | Admin? | Scope                |
| - | --------------------------------------------- | ------ | -------------------- |
| 1 | Install for current user (Startup folder)     | No     | This user only       |
| 2 | Install for current user (Scheduled Task)     | Yes    | This user only       |
| 3 | Install system wide (Scheduled Task)          | Yes    | Every user on the PC |

Pick mode 1 if you want zero UAC. Pick mode 2 for Task Scheduler
manageability. Pick mode 3 on a multi-user laptop. To remove: re-run
the installer and pick *Uninstall*.

See [`docs/installer.md`](docs/installer.md) for the full installer
documentation — file locations per mode, CLI reference, status output,
troubleshooting, build-from-source.

## Brightness behaviour

The EC adjusts keyboard backlight at the firmware level when Fn+Up/Down is
pressed. We cannot suppress that change — by the time the HID code reaches
Windows, the brightness has already moved. The daemon writes the brightness
back to a tracked `target_brightness` immediately afterwards.

- On launch, no brightness command is issued. The user's existing level is
  preserved.
- The internal `target_brightness` defaults to `0` (off) — matching the
  typical post-boot state of the GA401L.
- If your actual brightness differs from `target_brightness`, the *first*
  plain Fn+Up or Fn+Down will snap it to the tracker value (one visible
  step). After that, the tracker matches reality and restores are
  invisible.
- To anchor the tracker to a specific level, hit Ctrl+Fn+Up or Ctrl+Fn+Down
  once. Both update the tracker and step the EC to a known state.
- External changes (Armoury Crate, sleep/wake) cause the tracker to drift
  until the next Ctrl+Fn+Up/Down re-anchors. Acceptable in practice — see
  [`docs/adr/0007-state-tracking-for-brightness.md`](docs/adr/0007-state-tracking-for-brightness.md).

## Diagnostics — porting to a different ASUS model

If your laptop emits different Fn-combo codes, point the listener at your
HID interface and observe what arrives.

```
cd diagnostic
rye sync
rye run python hid_listener.py --log capture.log
```

(Requires [Rye](https://rye.astral.sh/) and runs on any Windows with the
ASUS keyboard present. The Python tool is read-only and needs no admin.)

Press your test sequence; compare the output against the captured codes in
[`docs/codes.md`](docs/codes.md). Adjust `FN_LEFT`, `FN_RIGHT`, `FN_UP`,
`FN_DOWN` constants in `src/main.rs` to match.

If your model uses an entirely different report ID, update
`ASUS_REPORT_ID` and `TARGET_PATH_FRAGMENT` in `src/main.rs`.

## Documentation

- [`docs/codes.md`](docs/codes.md) — HID code reference, decoded report
  formats, and the Aura brightness write protocol.
- [`docs/adr/`](docs/adr/) — architecture decision records covering each
  significant trade-off (HID vs keyboard hook, Rust choice, brightness
  handling, etc.).
- [`findings.md`](findings.md) — Stage 1 diagnostic narrative; what the
  capture revealed and why we trust it.

## Acknowledgements

The keyboard-brightness write byte sequence was verified against
[**G-Helper**](https://github.com/seerge/g-helper) by Sergey Mikhailov —
specifically `app/USB/Aura.cs` (`Aura.DirectBrightness`). G-Helper is the
de-facto open-source replacement for ASUS Armoury Crate and remains the
best reference for ASUS HID protocols.

## License

Apache License 2.0. See [`LICENSE`](LICENSE) for the full text and
[`NOTICE`](NOTICE) for attribution.

Copyright 2026 Pierre Kisters.

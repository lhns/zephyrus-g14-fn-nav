# Stage 1 — HID diagnostic findings

**Outcome:** Fn+arrow combinations on the ASUS Zephyrus G14 GA401L emit
distinct, observable HID codes. Stage 2A (custom Rust listener) is feasible.

## Test setup

- Tool: `diagnostic/hid_listener.py` (pywinusb), no admin required.
- Captured to `diagnostic/capture.log`.

## Key channels observed

| Device | Report ID | Purpose |
|---|---|---|
| `VID_0B05 PID_1866 MI_02 COL03` | `0x5D` | Standard keyboard, NKRO-like 31-byte report. Plain arrows arrive here. |
| `VID_0B05 PID_1866 MI_02 COL01` | `0x5A` | **ASUS-specific Fn-combo channel.** Fn+arrows arrive here. |
| `VID_0B05 PID_1866 MI_02 COL02` | `0x02` | Standard HID consumer (media keys). Mute / play / next-track / etc. |

## Report formats

### `COL03 rpt=0x5D` (regular keyboard, 31 bytes)

```
byte 0: 0x01            # constant report-type marker
byte 1: HID modifier    # standard 8-bit: Ctrl/Shift/Alt/GUI L+R
byte 2: extended mod    # 0x08 = Fn held
byte 3..30: HID usage IDs of currently pressed keys (NKRO)
```

Plain arrows confirm HID usage IDs in byte 3:
- Left = `0x50`, Right = `0x4F`, Up = `0x52`, Down = `0x51`.

When Fn+arrow is pressed, byte 2 = `0x08` but byte 3 stays `0x00` — the EC
suppresses the arrow on the standard channel.

### `COL01 rpt=0x5A` (ASUS Fn-combo channel, 5 bytes)

```
byte 0: action code (vendor-specific)
byte 1..4: 0
```

Key-down sends one report with the action code; key-up sends `[00 00 00 00 00]`.

## Fn+arrow → action code mapping (the answer)

| Combo | Code on COL01 |
|---|---|
| **Fn+Left** | **`0xB2`** |
| **Fn+Right** | **`0xB3`** |
| **Fn+Up** | **`0xC4`** |
| **Fn+Down** | **`0xC5`** |

## Other Fn-combo codes incidentally captured

| Combo | Channel | Code | Likely meaning |
|---|---|---|---|
| Fn+F1 (mute) | COL02 rpt=0x02 | `0xE2` | HID consumer: Mute (standard) |
| Fn+F4 | COL01 rpt=0x5A | `0xAE` | ASUS performance mode |
| Fn+F5 | COL02 rpt=0x02 | `0xB6` | HID consumer: Scan Previous Track |
| Fn+F7 | COL02 rpt=0x02 | `0xCD` | HID consumer: Play/Pause |

The ASUS-specific codes (0xAE, 0xB2, 0xB3, 0xC4, 0xC5) all arrive on the same
interface (COL01 / report 0x5A), which simplifies the listener.

## Heartbeat noise

- `COL01 rpt=0x5A [EC 02 00 00 00]` arrives every ~3 seconds when a Fn-aware
  key is held. Treat as keepalive; ignore.
- `COL03 rpt=0x5D [EC 02 00 ...]` similar. Ignore.

## Implications for Stage 2A

1. **Listener target:** open
   `\\?\hid#vid_0b05&pid_1866&mi_02&col01#...` and read reports with ID `0x5A`.
2. **Decode:** if `data[0] ∈ {0xB2, 0xB3, 0xC4, 0xC5}` → emit corresponding
   navigation key. If `data[0] == 0x00` → key-up (no action needed unless we
   later implement key-repeat). Drop `0xEC` heartbeats.
3. **Modifier passthrough:** Shift / Ctrl modifiers physically held during
   Fn+arrow remain visible on COL03 in the standard modifier byte and stay
   "down" from Windows' perspective, so a synthesized VK_END will naturally
   become Shift+End in apps that listen via the standard input stack. To be
   verified end-to-end after the listener is built.
4. **No admin required.** All ASUS HID interfaces opened with shared access.

## Collision test

A second capture (`diagnostic/capture-collision.log`, 515 lines, ~10 minutes
of varied input) was run with this protocol:

- **A.** Other Fn+keys (F2/F3/F6/F8/F9–F12, Esc, Tab, Space, Enter,
  Backspace, Delete, several letters and digits).
- **B.** Modifier-stacked Fn+arrows: Shift+Fn+arrow, Ctrl+Fn+arrow.
- **C.** ~3 minutes of random typing in a text editor (regular alphanumeric
  + modifiers).
- **D.** ASUS dedicated hardware keys (none present on GA401L beyond the
  F-row, but tapped anyway).

### Results

Filtered for `COL01 rpt=0x5A`, excluding heartbeat (`0xEC*`) and key-up
(`0x00*`):

| Code   | Trigger context                       | Count |
| ------ | ------------------------------------- | ----- |
| `0xB2` | Fn+Left (incl. with Shift, with Ctrl) | 3     |
| `0xB3` | Fn+Right (incl. with Shift, with Ctrl)| 2     |
| `0xC4` | Fn+Up   (with Shift)                  | 1     |
| `0xC5` | Fn+Down (with Shift)                  | 1     |
| `0x10` | Some Fn+other-key                     | 1     |
| `0x20` | Some Fn+other-key                     | 1     |
| `0x6B` | Some Fn+other-key (saw with LeftGUI on COL03) | 2 |

Random typing (Section C, ~180 seconds) produced **zero** `0x5A` reports
beyond heartbeat. Modifier-stacked Fn+arrow correctly emitted the same
B2/B3/C4/C5 with the modifier still visible on COL03's modifier byte —
modifier passthrough verified.

**Conclusion:** codes `0xB2 / 0xB3 / 0xC4 / 0xC5` are uniquely produced by
Fn+Left / Fn+Right / Fn+Up / Fn+Down respectively. No false-positive risk
in normal use.

## Behavioural notes

- **No hardware auto-repeat.** Holding Fn+Left for ~3 s produced exactly one
  key-down report (`B2`) at press and one key-up report (`00`) at release.
  The EC does not generate repeat events. If repeat is wanted, the listener
  must synthesise it (timer-driven). Home/End rarely need repeat; PgUp/PgDn
  is the realistic motivator. Deferred — see `docs/adr/0005-no-auto-repeat-in-v1.md`.
- **Heartbeat cadence.** `[EC 02 00 00 00]` arrives every ~3 s when the
  channel has had recent activity. Treated as keepalive and ignored.

# HID code reference — ASUS Zephyrus G14 (GA401L)

Empirical reference of HID reports observed on this specific laptop. All
captures via `diagnostic/hid_listener.py`. See `findings.md` (root) for the
diagnostic narrative; this file is the lookup table.

> Scope: codes listed here were captured *on this user's GA401L*. Other ASUS
> models may use a different scheme. Re-run the diagnostic before assuming
> compatibility with another machine.

## Devices

ASUS keyboard exposes itself as multiple HID *collections* under one USB
interface:

| Collection (HID path fragment)            | Report ID | Purpose                                        |
| ----------------------------------------- | --------- | ---------------------------------------------- |
| `vid_0b05&pid_1866&mi_02&col01`           | `0x5A`    | **ASUS-specific Fn-combo channel** (our hook). |
| `vid_0b05&pid_1866&mi_02&col02`           | `0x02`    | Standard HID Consumer Page (media keys).       |
| `vid_0b05&pid_1866&mi_02&col03`           | `0x5D`    | Extended keyboard report (NKRO + Fn state).    |
| `vid_0b05&pid_1866&mi_02&col04`           | —         | Not yet decoded; carries no observed traffic.  |
| `vid_0b05&pid_193b&col01..col02`          | —         | ITE 8910 Aura RGB controller. Not relevant.    |

The listener attaches **only to COL01**. Reports on other collections never
reach our process.

## COL01 / report `0x5A` (ASUS Fn-combo, 5-byte payload)

```
+--------+--------+--------+--------+--------+
| code   |  00    |  00    |  00    |  00    |
+--------+--------+--------+--------+--------+
   ^----- vendor action code (see table)
```

Key-down emits one report with the action code at byte 0; key-up emits
`[00 00 00 00 00]`.

### Action codes captured

| Code  | Trigger              | Used for           |
| ----- | -------------------- | ------------------ |
| `0xB2`| **Fn + Left**        | → emits `VK_HOME`  |
| `0xB3`| **Fn + Right**       | → emits `VK_END`   |
| `0xC4`| **Fn + Up**          | Ctrl held → bump `target_brightness` up; otherwise → emit `VK_PRIOR` and restore brightness. See ADR 0006. |
| `0xC5`| **Fn + Down**        | Ctrl held → bump `target_brightness` down; otherwise → emit `VK_NEXT` and restore brightness. |
| `0xAE`| Fn + F4              | ASUS performance-mode toggle. Not consumed. |
| `0x10`| Some Fn + key (TBD)  | Unmapped.          |
| `0x20`| Some Fn + key (TBD)  | Unmapped.          |
| `0x6B`| Some Fn + key (TBD, fired with LGui on COL03 — likely a Win-shortcut Fn+L/P/E equivalent) | Unmapped. |
| `0xEC`| Heartbeat / keepalive| Ignored.           |
| `0x00`| Key-up               | Ignored (no action). |

### Output side — keyboard brightness command

The same HID handle (COL01 / report `0x5A`) is used for output writes that
control keyboard backlight brightness. Byte sequence (verified against
G-Helper's `Aura.DirectBrightness` in `seerge/g-helper`):

```
[0x5A, 0xBA, 0xC5, 0xC4, level]   # level: 0 off, 1 low, 2 med, 3 high
```

Issued via `HidDevice::send_feature_report` on the same device opened for
input (plain output writes fail with `ERROR_INVALID_FUNCTION` — the device
exposes report ID `0x5A` as Input + Feature, not Output). The listener
writes this only after a plain Fn+Up/Down press, restoring brightness to
the in-process `target_brightness`. No startup write — the user's
existing level is preserved.

> **Collision test:** the codes `0xB2 / 0xB3 / 0xC4 / 0xC5` were *not* seen
> from any non-Fn+arrow source during the expanded collision capture. See
> `findings.md` § Collision test for the test protocol and the full result
> table.

### Repeat behaviour

The EC does **not** auto-repeat Fn+arrow when held. Hold Fn+Left for 3 s →
one `B2` at press, one `00` at release, no intermediate repeats. If repeat
is ever desired (PgUp/PgDn for fast scrolling), it has to be synthesised
client-side. See ADR 0005.

## COL03 / report `0x5D` (extended keyboard, 31-byte payload)

```
byte 0: 0x01           # constant report-type marker
byte 1: HID modifier   # standard 8-bit Ctrl/Shift/Alt/GUI L+R
byte 2: extended mod   # 0x08 = Fn held
byte 3..30: HID Usage IDs of currently pressed keys (NKRO)
```

### HID modifier byte (byte 1) bits

| Bit | Modifier        |
| --- | --------------- |
| 0   | Left  Ctrl      |
| 1   | Left  Shift     |
| 2   | Left  Alt       |
| 3   | Left  GUI (Win) |
| 4   | Right Ctrl      |
| 5   | Right Shift     |
| 6   | Right Alt       |
| 7   | Right GUI       |

### Extended modifier byte (byte 2)

| Value | Meaning              |
| ----- | -------------------- |
| `0x08`| **Fn held**          |
| `0x00`| no extended modifier |

### Notable HID Usage IDs (byte 3+)

Standard HID Keyboard Page values — listed only for the keys we touched.

| Usage | Key   |
| ----- | ----- |
| `0x4F`| Right Arrow |
| `0x50`| Left Arrow  |
| `0x51`| Down Arrow  |
| `0x52`| Up Arrow    |
| `0x07`| D     |
| `0x08`| E     |
| `0x11`| N     |
| `0x12`| O     |
| `0x17`| T     |
| `0x18`| U     |
| `0x28`| Enter |
| `0x2A`| Backspace |
| `0x2B`| Tab   |

> **Important property:** when **Fn+arrow** is pressed, byte 2 reads `0x08`
> but byte 3 stays `0x00` — i.e. the arrow itself is *suppressed* on COL03.
> The Fn+arrow combo is delivered exclusively as a vendor code on COL01.
> This is why our listener sees a clean signal with no double-fire.

## COL02 / report `0x02` (HID Consumer Page, 4-byte payload)

Standard HID Consumer Page. Codes captured during diagnostic:

| Code   | Trigger    | Standard meaning            |
| ------ | ---------- | --------------------------- |
| `0xE2` | Fn + F1    | Mute                        |
| `0xB6` | Fn + F5    | Scan Previous Track         |
| `0xCD` | Fn + F7    | Play / Pause                |
| `0xB5` | (variant)  | Scan Next Track             |

Not consumed by our listener.

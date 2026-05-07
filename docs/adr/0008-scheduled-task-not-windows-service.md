# 8. Auto-start via Scheduled Task at user logon, not a Windows Service

Date: 2026-05-07

## Status

Accepted.

## Context

The listener needs to start automatically at login. The user's first
instinct was a Windows Service. That doesn't work here:

- Windows Services run in **Session 0**, isolated from interactive
  desktops since Windows Vista.
- `SendInput` calls from Session 0 do not reach the user's interactive
  session — synthesised Home/End/PgUp/PgDn would never appear in any
  app.
- The standard workaround (a service that spawns a user-session helper
  via `CreateProcessAsUser` / `WTSCreateProcess`) is disproportionate
  complexity for a single-user keyboard helper.

Alternatives considered:

| Option | Pro | Con |
| --- | --- | --- |
| Startup folder shortcut | Simplest | Visible console window unless wrapped |
| `HKCU\…\Run` registry key | Same simplicity, slightly more hidden | Same console-visibility issue |
| Scheduled Task at logon | Manageable via Task Scheduler UI; idempotent re-install with `/F`; can run hidden via VBS wrapper | Slightly more script in the installer |

## Decision

Register a per-user Scheduled Task triggered `ONLOGON`, whose action is
`wscript.exe %LOCALAPPDATA%\zephyrus-g14-fn-nav\start.vbs`. The VBS is
two lines and uses `WScript.Shell.Run "...exe", 0, False` to launch the
listener with a hidden window without waiting.

```
schtasks /Create /TN "ZephyrusG14FnNav"
                 /TR "wscript.exe \"%DEST%\start.vbs\""
                 /SC ONLOGON /F
```

Install location: `%LOCALAPPDATA%\zephyrus-g14-fn-nav\` — per-user, no
admin / UAC required *for the listener at runtime*.

> **Install-time elevation:** `schtasks /Create` requires admin on the
> author's machine even with `/RU "%USERNAME%"` — locked-down config
> common in corporate / German Windows installs. The installer
> self-elevates via `ShellExecute "...", "...", "", "runas", 1` (UAC
> prompt). Once elevated, the task is created with `/RU` referencing
> the original user, so it still runs in the user's session at logon.
> The elevation is one-time during install; the listener itself never
> needs admin. The `--noelevate` re-entry guard prevents an infinite
> elevation loop.

## Consequences

- The console-mode binary is preserved unchanged. Manual debug runs
  from a terminal still show the Ctrl+Fn+Up/Down debug prints; only the
  auto-start path hides the window.
- Task is visible in Task Scheduler UI for inspection, manual
  enable/disable, and clean removal.
- `/F` makes re-install idempotent — running the installer again
  cleanly replaces the existing task.
- VBS wrapper avoids needing to rebuild the binary as
  `windows_subsystem = "windows"`, which would silently drop stderr
  panics — undesirable in a tool that does HID I/O and may legitimately
  fail at startup if the device is unavailable.
- We coexist with Armoury Crate / G-Helper because the task runs in the
  user session and reads/writes the shared HID handle.

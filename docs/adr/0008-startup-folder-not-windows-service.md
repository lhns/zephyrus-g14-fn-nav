# 8. Auto-start via the Startup folder, not a Windows Service or Scheduled Task

Date: 2026-05-07

## Status

Accepted.

## Context

The listener needs to start automatically at login. Three Windows-side
mechanisms were considered:

1. **Windows Service.** Initial user proposal. Doesn't work: services
   run in **Session 0**, isolated from interactive desktops since
   Windows Vista. `SendInput` calls from Session 0 do not reach the
   user's session — synthesised Home/End/PgUp/PgDn would never appear
   in any app. Working around this via `CreateProcessAsUser` /
   `WTSCreateProcess` is disproportionate complexity for a single-user
   keyboard helper.

2. **Scheduled Task** (`schtasks /Create /SC ONLOGON`). Manageable via
   Task Scheduler UI; idempotent re-install with `/F`. **But:** on the
   author's Win11 machine, registering a `LogonTrigger` requires admin
   even with `/RU "%USERNAME%" /IT`. Empirically tested — `schtasks`
   returns "access denied" for `/SC ONLOGON` while `/SC ONCE` succeeds
   without elevation. This is a Windows security policy on locked-down
   configurations (typical for corporate / German Windows installs)
   and not worth bypassing with a UAC prompt at install time when a
   simpler no-admin alternative exists.

3. **Startup folder.** A `.vbs` file dropped into
   `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\` is run by
   `wscript` at every user logon. No admin, no UAC, no service — just
   a file in a well-known location.

## Decision

Use the Startup folder. The installer:

1. Extracts the binary to `%LOCALAPPDATA%\zephyrus-g14-fn-nav\`.
2. Writes `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\zephyrus-g14-fn-nav.vbs`
   — two lines that call
   `WScript.Shell.Run "...exe", 0, False`
   (style 0 = hidden window, False = don't wait for exit).

Uninstall deletes the `.vbs` and the install directory.

## Consequences

- **No admin / no UAC at install time.** The entire flow is
  per-user, in per-user-writable locations.
- **Console-mode binary unchanged.** Manual debug runs from a terminal
  still print Ctrl+Fn+Up/Down debug messages; only the auto-start
  path hides the window via the VBS wrapper.
- **No auto-restart on crash.** The Scheduled Task option had a
  configurable restart-on-failure setting. The blocking-read loop in
  the listener is robust; if it ever crashes, the next logon
  re-launches it. Acceptable for v1.
- **Discoverable autostart entry.** Visible in
  `Settings -> Apps -> Startup` ("Windows Script Host" / the .vbs
  filename). Users who clean up startups can disable it without
  editing scripts.
- **Coexists** with Armoury Crate / G-Helper because everything runs
  in the user's interactive session and shares the HID handle.

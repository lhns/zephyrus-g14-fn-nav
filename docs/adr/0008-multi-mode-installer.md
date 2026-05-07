# 8. Multi-mode installer (three install modes, conditional elevation)

Date: 2026-05-07

## Status

Accepted.

## Context

The listener needs to start automatically at login. Three Windows
mechanisms were considered up-front:

1. **Windows Service.** User's recurring instinct, including after
   admin-required obstacles came up. **Doesn't work even with admin.**
   Services run in **Session 0**, isolated from interactive desktops
   since Windows Vista. `SendInput` calls from Session 0 do not reach
   the user's session; synthesised Home/End/PgUp/PgDn would never
   appear in any app. The legacy "Allow service to interact with
   desktop" tickbox was deliberately neutered when Session 0 was
   introduced. To make a service work, it would have to spawn a
   user-session helper via `CreateProcessAsUser` /
   `WTSCreateProcess` — which is structurally a "Scheduled Task with
   extra moving parts" and brings no functional advantage over a
   plain Scheduled Task.

2. **Scheduled Task at user logon** (`schtasks /Create /SC ONLOGON`).
   Manageable via Task Scheduler UI; idempotent re-install with `/F`.
   **Empirically requires admin** on locked-down Win11 even with
   `/RU "%USERNAME%" /IT` — tested:

       schtasks /Create /SC ONLOGON /RU username /IT /F  -> Zugriff verweigert
       schtasks /Create /SC ONCE  /ST 23:59 /F           -> success

   `LogonTrigger` registration specifically. Cannot be worked around
   via XML import (`schtasks /XML`), PowerShell `Register-ScheduledTask`,
   or COM Schedule.Service — all hit the same Windows policy. So if
   we want this mechanism, the user signs one UAC prompt at install.

3. **Startup folder.** A `.vbs` file dropped into
   `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\` is run
   by `wscript` at every user logon. No admin, no service. Loses
   Task Scheduler manageability.

### Design history (kept visible — not airbrushed away)

Earlier iterations of this work flip-flopped:

- First sketch: ship `.exe` + `install.bat` side-by-side, copy a
  shortcut to Startup folder.
- Then: replace with self-extracting `.bat` (per the daslight
  reference) registering a Scheduled Task at logon. Hit the empirical
  admin requirement; silently added a self-elevation block.
- User flagged the unauthorised elevation; switched to Startup folder
  to avoid admin entirely. User flagged that I'd silently changed the
  mechanism without asking.
- Now: expose all three as user-selectable modes, document the
  trade-offs honestly, capture the obstacles instead of silently
  routing around them.

The flip-flopping is preserved in this ADR because (a) the user
explicitly asked obstacles be documented in ADRs not silently worked
around, and (b) the multi-mode design exists *because* of those
obstacles — pretending the trial-and-error didn't happen would erase
the rationale for offering all three.

## Decision

Ship a single self-extracting `.bat` installer that offers **three
installation modes**. The user picks at install time:

| # | Auto-start mechanism                              | Install dir                          | Admin? | Scope                |
| - | ------------------------------------------------- | ------------------------------------ | ------ | -------------------- |
| 1 | Startup folder (`.vbs`)                           | `%LOCALAPPDATA%\zephyrus-g14-fn-nav\`| No     | Current user         |
| 2 | Scheduled Task `/SC ONLOGON /RU username`         | `%LOCALAPPDATA%\zephyrus-g14-fn-nav\`| Yes    | Current user         |
| 3 | Scheduled Task XML, `<GroupId>S-1-5-32-545</GroupId>` (Users), `<LogonTrigger>`, `Parallel` MultipleInstancesPolicy | `%ProgramFiles%\zephyrus-g14-fn-nav\` | Yes | Every user on the PC |

### Sub-decisions baked into this ADR

**Lazy elevation.** UAC fires only when the chosen action genuinely
requires it. Mode 1 install never elevates. Mode 2/3 install elevates
once after the user explicitly picks the option. Uninstall elevates
only if a Scheduled Task or `%ProgramFiles%` install is detected. The
interactive menu elevates *after* the user makes a choice, not before
the menu renders — so the user can read the options without UAC
flashing in their face.

**VBS wrapper for *all* modes.** Scheduled Task `<Hidden>true</Hidden>`
hides the *task* in Task Scheduler UI but does **not** suppress the
console window of the binary the task spawns. The cleanest console
suppressor on Windows is `wscript.exe` running a two-line VBS that
calls `WScript.Shell.Run "...exe", 0, False`. Alternatives (PowerShell
`-WindowStyle Hidden`, `Start-Process -WindowStyle Hidden`) flash a
window briefly. Compiling a `windows_subsystem = "windows"` binary
would lose stderr-on-startup visibility. Conclusion: keep VBS for all
three modes; the same two-line `start.vbs` regardless of where it
lives.

**Mode-agnostic uninstall.** Uninstall probes for *every* artifact any
mode could have written and removes whatever's present. Rationale:
handles interrupted installs (e.g. `.exe` extracted but task creation
crashed), cross-mode residue (someone installed Mode 1 then Mode 2
without uninstalling between), and a future user who downloads the
installer just to clean up an old install. Simpler invariant than
storing an "installed mode" marker file and trying to do mode-specific
removal.

**No upgrade-in-place.** If the user wants to switch modes, they run
uninstall then re-install. Supporting in-place mode migration would
require synchronizing across all three artefact sets and is YAGNI.

## Consequences

- **Choice surfaces the trade-off rather than choosing for the user.**
  Three modes is more menu UX than one mode, but each is a real and
  defensible choice. Users who hate UAC have an out (mode 1); users
  who want manageability accept one prompt (mode 2); multi-user
  laptops get a real system-wide install (mode 3).
- **One UAC prompt at install / uninstall for modes 2/3.** Acceptable
  trade-off, documented up front so future readers don't try to
  remove the elevation block thinking it's vestigial.
- **`/RU "%USERNAME%"` on mode 2** — when run via UAC, the elevated
  process retains the original user identity (UAC elevates the token,
  not the user), so `%USERNAME%` resolves correctly. The created task
  is owned by the elevated admin context but `/RU` makes it run *as*
  the original user.
- **System-wide mode (3) needs XML, not command-line schtasks.**
  The `<GroupId>` principal isn't expressible via `/RU`. The XML is
  embedded as a second base64 payload in the installer (see ADR 0009)
  and decoded at install time only when mode 3 is chosen.
- **The Service question is settled.** If a future contributor or
  another fork proposes a Service-based architecture, they can be
  pointed at the "Why not Service" item in this ADR's Context.

# Installer

`zephyrus-g14-fn-nav` is distributed as a single self-extracting `.bat`.
Download from the latest [Release](https://github.com/lhns/zephyrus-g14-fn-nav/releases),
double-click, pick a mode. To remove, double-click again — the menu will
offer Uninstall.

## Quick start

1. Download `install-zephyrus-g14-fn-nav-vX.Y.Z.bat`.
2. Double-click. Pick **[1] Install for current user (Startup folder)**
   if you don't want to deal with UAC. Pick **[2]** if you want it
   managed via Task Scheduler. Pick **[3]** if multiple users on the
   machine should get the listener.
3. Press Fn+Right in any text editor — the cursor jumps to End. Done.

## The three install modes

| # | Mode                                             | Auto-start mechanism                         | Install dir                          | Admin? | Scope                |
| - | ------------------------------------------------ | -------------------------------------------- | ------------------------------------ | ------ | -------------------- |
| 1 | Install for current user (Startup folder)        | `.vbs` in the user's Startup folder          | `%LOCALAPPDATA%\zephyrus-g14-fn-nav\`| No     | This user only       |
| 2 | Install for current user (Scheduled Task)        | Scheduled Task at logon for the current user | `%LOCALAPPDATA%\zephyrus-g14-fn-nav\`| Yes    | This user only       |
| 3 | Install system wide (Scheduled Task)             | Scheduled Task at logon for the Users group  | `%ProgramFiles%\zephyrus-g14-fn-nav\`| Yes    | Every user on the PC |

### When to pick each

- **Mode 1** is the simplest. Pick it if you don't want to deal with UAC
  and the laptop is single-user (typical for a personal G14). The
  autostart entry is visible in `Settings -> Apps -> Startup` and easy
  to inspect or disable.
- **Mode 2** trades one UAC prompt at install time for Task Scheduler
  manageability (start/stop/inspect via `Task Scheduler` UI or
  `schtasks /Query /TN ZephyrusG14FnNav`). Same install location as
  mode 1; differs only in the autostart mechanism.
- **Mode 3** writes to `Program Files` and registers a per-Users-group
  task — the listener auto-starts for every user who logs in, not just
  the one who installed it. Pick this on a multi-user laptop. Needs
  one UAC prompt at install.

The choice is one-time per install. To switch modes, run uninstall first.

## File locations per mode

| File                                                                      | Mode 1 | Mode 2 | Mode 3 |
| ------------------------------------------------------------------------- | :----: | :----: | :----: |
| `%LOCALAPPDATA%\zephyrus-g14-fn-nav\zephyrus-g14-fn-nav.exe`              |   ✓    |   ✓    |        |
| `%LOCALAPPDATA%\zephyrus-g14-fn-nav\start.vbs`                            |        |   ✓    |        |
| `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\zephyrus-g14-fn-nav.vbs` | ✓ |    |        |
| `%ProgramFiles%\zephyrus-g14-fn-nav\zephyrus-g14-fn-nav.exe`              |        |        |   ✓    |
| `%ProgramFiles%\zephyrus-g14-fn-nav\start.vbs`                            |        |        |   ✓    |
| Scheduled Task `ZephyrusG14FnNav`                                         |        |   ✓    |   ✓    |

## Command-line reference

The installer accepts flags so it can be scripted:

```
install-zephyrus-g14-fn-nav-vX.Y.Z.bat                     # interactive menu
install-zephyrus-g14-fn-nav-vX.Y.Z.bat --status            # print status, exit
install-zephyrus-g14-fn-nav-vX.Y.Z.bat --install startup        # mode 1
install-zephyrus-g14-fn-nav-vX.Y.Z.bat --install task-user      # mode 2 (UAC)
install-zephyrus-g14-fn-nav-vX.Y.Z.bat --install task-system    # mode 3 (UAC)
install-zephyrus-g14-fn-nav-vX.Y.Z.bat --uninstall              # remove (UAC if needed)
```

The interactive menu calls the same code paths after the user picks an
option.

## Status output

`--status` prints one of:

- `Status: NOT INSTALLED`
- `Status: INSTALLED [Startup folder, current user] at ...`
- `Status: INSTALLED [Scheduled Task, current user] at ...`
- `Status: INSTALLED [Scheduled Task, system wide] at ...`
- `Status: INSTALLED [partial / inconsistent] - uninstall will clean up`

The "partial / inconsistent" case shows up if a previous install was
interrupted (e.g. the .exe was extracted but the autostart artifact
wasn't created) or if cross-mode residue exists. Run uninstall — it
removes everything regardless of which mode is currently "officially"
active.

## Uninstall behaviour

Uninstall is **mode-agnostic**. It probes for every artifact any of the
three modes could have written and removes whatever's present:

- stops any running listener (`taskkill /F /IM zephyrus-g14-fn-nav.exe`),
- deletes the Startup-folder VBS,
- deletes the Scheduled Task,
- removes `%LOCALAPPDATA%\zephyrus-g14-fn-nav\`,
- removes `%ProgramFiles%\zephyrus-g14-fn-nav\`.

This handles the normal case, interrupted-install residue, and
cross-mode leftovers. UAC fires only if a Scheduled Task or a
`%ProgramFiles%` install is detected (deleting either needs admin).

## When UAC fires

| Action                          | UAC? |
| ------------------------------- | :--: |
| `--status`                      | Never |
| `--install startup`             | Never |
| Mode-1 path through the menu    | Never |
| `--install task-user`           | Once |
| `--install task-system`         | Once |
| Mode-2 / Mode-3 menu selection  | Once, *after* the user picks the option |
| `--uninstall` of mode-1 install | Never |
| `--uninstall` of mode-2 / 3     | Once |
| Re-running an already-installed installer | Never (status check is read-only) |

The lazy-elevation rule: UAC fires only when the chosen action genuinely
needs admin. Mode 1 stays admin-free end to end. The interactive menu
defers UAC until *after* the user picks a needs-admin option, so you can
read the menu before being prompted.

## Troubleshooting

**"Zugriff verweigert" / "Access denied" from `schtasks`.**
Mode 2 and Mode 3 require admin. Either pick mode 1, or click Yes on
the UAC prompt. See ADR 0008 for why `LogonTrigger` registration needs
admin even with `/RU "%USERNAME%"` on locked-down Windows configs.

**Listener isn't running after install.**
Check `tasklist /FI "IMAGENAME eq zephyrus-g14-fn-nav.exe"`. If empty:

- For mode 1: open the Startup folder
  (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`) and
  double-click `zephyrus-g14-fn-nav.vbs` — should launch silently.
- For modes 2/3: open Task Scheduler, find `ZephyrusG14FnNav`, right-click
  → Run. If that fails, check the task's Last Run Result.

**Console window appears at logon.**
Shouldn't — the VBS wrapper hides it. If you see one, you may have
double-clicked the .exe directly instead of launching it via the
installed `start.vbs`.

**Re-installing without uninstalling.**
The installer doesn't support upgrade-in-place between modes. Run
`--uninstall` first, then install the new mode.

**Filename has parentheses (e.g. `install (1).bat`).**
The installer rejects this with a clear error. Browsers add `(1)` to
re-downloaded files, and `cmd.exe`'s block parser breaks on unmatched
parens — even in the script's own filename. Rename and try again.

## Build from source

For developers / contributors:

```
cargo build --release
python scripts/package.py --exe target/release/zephyrus-g14-fn-nav.exe
```

Produces `install-zephyrus-g14-fn-nav-dev.bat` at the repo root. Pass
a `--version` to get a different suffix:

- `--version v0.1.0` → `install-zephyrus-g14-fn-nav-v0.1.0.bat`
  (matches the release-build format).
- `--version dev-$(git rev-parse --short HEAD)` →
  `install-zephyrus-g14-fn-nav-dev-1d8a0fd.bat` (matches the CI-build
  format).

The packager embeds two base64 payloads in the output `.bat`: the .exe
itself, and the `task.xml` for mode 3. Both are decoded at runtime via
`certutil -decode` (a built-in Windows utility, no external
dependencies). See ADR 0009 for the design rationale.

## How it works under the hood

The installer is a self-extracting `.bat` produced by `scripts/package.py`.
At runtime:

1. Validates filename (rejects parens — see above).
2. Dispatches on the `--install` / `--uninstall` / `--status` flag, or
   shows the interactive menu.
3. Detects what's currently installed by probing all four artifacts.
4. For install: extracts the .exe (and, for mode 3, the task XML) from
   embedded base64 via `certutil -decode`, writes the VBS launcher,
   creates the autostart entry per the chosen mode.
5. For uninstall: kills the listener, deletes every artifact any mode
   could have created.

Self-elevation, when needed, uses the standard `WScript.Shell.ShellExecute
"...", "...", "", "runas", 1` pattern via a temp VBS — same trick as the
reference `install-daslight-shim.bat`. A `--noelevate` flag prevents an
infinite re-elevation loop.

#!/usr/bin/env python3
"""Package zephyrus-g14-fn-nav.exe into a self-extracting install.bat.

The installer offers three install modes (see docs/installer.md and ADR
0008): Startup folder current-user, Scheduled Task current-user (UAC),
and Scheduled Task system-wide (UAC + Program Files install).

Two payloads are embedded as base64 inside the .bat:
- {PAYLOAD_BASE64}     -> zephyrus-g14-fn-nav.exe (always extracted)
- {TASK_XML_BASE64}    -> task.xml (extracted only when mode 3 is chosen)
"""

import argparse
import base64
import sys
from pathlib import Path

INSTALLER_TEMPLATE = r'''@echo off
setlocal enabledelayedexpansion

:: Reject filenames with parentheses - they break cmd.exe block parsing.
:: Browsers append "(1)" etc. on re-download; the user must rename first.
echo "%~f0" | findstr /R "[()]" >nul && (
    echo [ERROR] The installer filename contains parentheses.
    echo         Please rename the file to remove them and try again.
    pause
    exit /b 1
)

set "TASK_NAME=ZephyrusG14FnNav"
set "EXE_NAME=zephyrus-g14-fn-nav.exe"
set "LOCAL_DEST=%LOCALAPPDATA%\zephyrus-g14-fn-nav"
set "PROGRAMFILES_DEST=%ProgramFiles%\zephyrus-g14-fn-nav"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "STARTUP_VBS=%STARTUP_DIR%\zephyrus-g14-fn-nav.vbs"

echo === zephyrus-g14-fn-nav installer v{APP_VERSION} ===
echo(

:: --- top-level elevation check -------------------------------------
:: Decide whether the requested CLI invocation needs admin. If yes and
:: not already elevated (and not in the --noelevate re-entry phase),
:: re-launch via UAC. Interactive menu (no args) skips this check;
:: menu options re-dispatch via "%~f0" --install <mode> which then
:: lands here with args set.
set "_NEEDS_ADMIN=0"
if /i "%~1 %~2"=="--install task-user"   set "_NEEDS_ADMIN=1"
if /i "%~1 %~2"=="--install task-system" set "_NEEDS_ADMIN=1"
if /i "%~1"=="--uninstall" (
    schtasks /Query /TN "%TASK_NAME%" >nul 2>&1 && set "_NEEDS_ADMIN=1"
    if exist "%PROGRAMFILES_DEST%" set "_NEEDS_ADMIN=1"
)
echo %* | findstr /C:"--noelevate" >nul && set "_NEEDS_ADMIN=0"
if "%_NEEDS_ADMIN%"=="1" (
    net session >nul 2>&1
    if not !ERRORLEVEL! EQU 0 (
        echo Requesting administrator privileges...
        set "_VBS=%TEMP%\zephyrus-g14-fn-nav-elevate-%RANDOM%.vbs"
        echo Set s=CreateObject^("Shell.Application"^):s.ShellExecute "%~f0","%* --noelevate","","runas",1 > "!_VBS!"
        wscript "!_VBS!"
        del "!_VBS!" 2>nul
        exit /b 0
    )
)

:: --- argument dispatch ---------------------------------------------
if "%~1"=="--status"    goto :status
if "%~1"=="--uninstall" goto :uninstall
if "%~1"=="--install" (
    if /i "%~2"=="startup"     goto :install_startup
    if /i "%~2"=="task-user"   goto :install_task_user
    if /i "%~2"=="task-system" goto :install_task_system
    echo [ERROR] --install requires a mode: startup ^| task-user ^| task-system
    exit /b 1
)

:: No args: interactive menu
goto :menu

:menu
call :detect
if "%ANY%"=="1" (
    echo Status: !STATUS_LABEL!
    echo(
    echo   [1] Uninstall
    echo   [0] Cancel
    echo(
    set /p "CHOICE=Select: "
    if "!CHOICE!"=="1" (
        "%~f0" --uninstall
        exit /b 0
    )
    echo Cancelled.
    pause
    exit /b 0
)
echo Status: NOT INSTALLED
echo(
echo Choose install mode:
echo   [1] Install for current user ^(Startup folder^)
echo   [2] Install for current user ^(Scheduled Task^)        ^(Admin permissions required^)
echo   [3] Install system wide ^(Scheduled Task^)             ^(Admin permissions required^)
echo   [0] Cancel
echo(
set /p "CHOICE=Select: "
:: Re-dispatch to CLI form so the top-level elevation check runs for
:: needs-admin modes - UAC fires after the user's choice, not before
:: the menu renders.
if "!CHOICE!"=="1" (
    "%~f0" --install startup
    exit /b 0
)
if "!CHOICE!"=="2" (
    "%~f0" --install task-user
    exit /b 0
)
if "!CHOICE!"=="3" (
    "%~f0" --install task-system
    exit /b 0
)
echo Cancelled.
pause
exit /b 0

:: --- detect what's installed ----------------------------------------
:detect
set "FOUND_STARTUP=0"
set "FOUND_TASK=0"
set "FOUND_LOCAL=0"
set "FOUND_PROGFILES=0"
if exist "%STARTUP_VBS%"               set "FOUND_STARTUP=1"
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1 && set "FOUND_TASK=1"
if exist "%LOCAL_DEST%\%EXE_NAME%"        set "FOUND_LOCAL=1"
if exist "%PROGRAMFILES_DEST%\%EXE_NAME%" set "FOUND_PROGFILES=1"
set "ANY=0"
if "%FOUND_STARTUP%"=="1"   set "ANY=1"
if "%FOUND_TASK%"=="1"      set "ANY=1"
if "%FOUND_LOCAL%"=="1"     set "ANY=1"
if "%FOUND_PROGFILES%"=="1" set "ANY=1"
if "%FOUND_TASK%"=="1" (
    if "%FOUND_PROGFILES%"=="1" (
        set "STATUS_LABEL=INSTALLED [Scheduled Task, system wide] at %PROGRAMFILES_DEST%"
    ) else (
        set "STATUS_LABEL=INSTALLED [Scheduled Task, current user] at %LOCAL_DEST%"
    )
) else if "%FOUND_STARTUP%"=="1" (
    set "STATUS_LABEL=INSTALLED [Startup folder, current user] at %LOCAL_DEST%"
) else if "%ANY%"=="1" (
    set "STATUS_LABEL=INSTALLED [partial / inconsistent] - uninstall will clean up"
) else (
    set "STATUS_LABEL=NOT INSTALLED"
)
exit /b 0

:status
call :detect
echo Status: !STATUS_LABEL!
exit /b 0

:: --- extract the embedded .exe payload to a target dir ---------------
:: %~1 is the destination directory (already exists)
:extract_exe
mkdir "%TEMP%\zephyrus-g14-fn-nav-%RANDOM%-extract" 2>nul
set "TEMP_DIR=%TEMP%\zephyrus-g14-fn-nav-%RANDOM%-extract"
mkdir "%TEMP_DIR%" 2>nul
setlocal disabledelayedexpansion
set "FOUND="
(for /f "usebackq tokens=*" %%L in ("%~f0") do (
    if defined FOUND (
        if "%%L"=="::PAYLOAD_END" goto :_extract_exe_done
        echo %%L
    )
    if "%%L"=="::PAYLOAD_START" set "FOUND=1"
)) > "%TEMP_DIR%\payload.b64"
:_extract_exe_done
endlocal & set "TEMP_DIR=%TEMP_DIR%"
certutil -decode "%TEMP_DIR%\payload.b64" "%~1\%EXE_NAME%" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] certutil -decode of exe payload failed.
    rmdir /S /Q "%TEMP_DIR%" 2>nul
    exit /b 1
)
rmdir /S /Q "%TEMP_DIR%" 2>nul
exit /b 0

:: --- extract the task XML payload to a target file ------------------
:: %~1 is the destination .xml file path
:extract_task_xml
set "TEMP_DIR=%TEMP%\zephyrus-g14-fn-nav-%RANDOM%-xml"
mkdir "%TEMP_DIR%" 2>nul
setlocal disabledelayedexpansion
set "FOUND="
(for /f "usebackq tokens=*" %%L in ("%~f0") do (
    if defined FOUND (
        if "%%L"=="::TASK_XML_END" goto :_extract_xml_done
        echo %%L
    )
    if "%%L"=="::TASK_XML_START" set "FOUND=1"
)) > "%TEMP_DIR%\task.b64"
:_extract_xml_done
endlocal & set "TEMP_DIR=%TEMP_DIR%"
certutil -decode "%TEMP_DIR%\task.b64" "%~1" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] certutil -decode of task XML payload failed.
    rmdir /S /Q "%TEMP_DIR%" 2>nul
    exit /b 1
)
rmdir /S /Q "%TEMP_DIR%" 2>nul
exit /b 0

:: --- write the hidden-window VBS launcher next to the binary --------
:: %~1 is the install dir
:write_start_vbs
> "%~1\start.vbs" echo Set sh = CreateObject("WScript.Shell")
>> "%~1\start.vbs" echo sh.Run """%~1\%EXE_NAME%""", 0, False
exit /b 0

:: --- mode 1: Startup folder, current user ---------------------------
:install_startup
echo Installing for current user (Startup folder)...
taskkill /F /IM "%EXE_NAME%" >nul 2>&1
if not exist "%LOCAL_DEST%" mkdir "%LOCAL_DEST%"
call :extract_exe "%LOCAL_DEST%"
if errorlevel 1 ( pause & exit /b 1 )
if not exist "%STARTUP_DIR%" mkdir "%STARTUP_DIR%"
> "%STARTUP_VBS%" echo Set sh = CreateObject("WScript.Shell")
>> "%STARTUP_VBS%" echo sh.Run """%LOCAL_DEST%\%EXE_NAME%""", 0, False
wscript.exe "%STARTUP_VBS%"
echo(
echo [OK] Installed.
echo      Binary:    %LOCAL_DEST%\%EXE_NAME%
echo      Autostart: %STARTUP_VBS%
:: Pause if invoked interactively (no args) or via the elevated re-launch
:: (so the freshly-popped UAC console doesn't vanish before the user
:: sees the result).
if "%~1"=="" pause
echo %* | findstr /C:"--noelevate" >nul && pause
exit /b 0

:: --- mode 2: Scheduled Task, current user ---------------------------
:install_task_user
echo Installing for current user (Scheduled Task)...
taskkill /F /IM "%EXE_NAME%" >nul 2>&1
if not exist "%LOCAL_DEST%" mkdir "%LOCAL_DEST%"
call :extract_exe "%LOCAL_DEST%"
if errorlevel 1 ( pause & exit /b 1 )
call :write_start_vbs "%LOCAL_DEST%"
schtasks /Create /TN "%TASK_NAME%" /TR "wscript.exe \"%LOCAL_DEST%\start.vbs\"" /SC ONLOGON /RU "%USERNAME%" /F >nul
if errorlevel 1 (
    echo [ERROR] schtasks /Create failed.
    pause
    exit /b 1
)
wscript.exe "%LOCAL_DEST%\start.vbs"
echo(
echo [OK] Installed.
echo      Binary: %LOCAL_DEST%\%EXE_NAME%
echo      Task:   %TASK_NAME% ^(runs as %USERNAME% at logon^)
:: Pause if invoked interactively (no args) or via the elevated re-launch
:: (so the freshly-popped UAC console doesn't vanish before the user
:: sees the result).
if "%~1"=="" pause
echo %* | findstr /C:"--noelevate" >nul && pause
exit /b 0

:: --- mode 3: Scheduled Task XML, system wide ------------------------
:install_task_system
echo Installing system wide (Scheduled Task)...
taskkill /F /IM "%EXE_NAME%" >nul 2>&1
if not exist "%PROGRAMFILES_DEST%" mkdir "%PROGRAMFILES_DEST%"
call :extract_exe "%PROGRAMFILES_DEST%"
if errorlevel 1 ( pause & exit /b 1 )
call :write_start_vbs "%PROGRAMFILES_DEST%"
set "XML_PATH=%TEMP%\zephyrus-g14-fn-nav-task-%RANDOM%.xml"
call :extract_task_xml "%XML_PATH%"
if errorlevel 1 ( pause & exit /b 1 )
schtasks /Create /TN "%TASK_NAME%" /XML "%XML_PATH%" /F >nul
if errorlevel 1 (
    echo [ERROR] schtasks /Create from XML failed.
    del "%XML_PATH%" 2>nul
    pause
    exit /b 1
)
del "%XML_PATH%" 2>nul
wscript.exe "%PROGRAMFILES_DEST%\start.vbs"
echo(
echo [OK] Installed.
echo      Binary: %PROGRAMFILES_DEST%\%EXE_NAME%
echo      Task:   %TASK_NAME% ^(runs at logon for any user^)
:: Pause if invoked interactively (no args) or via the elevated re-launch
:: (so the freshly-popped UAC console doesn't vanish before the user
:: sees the result).
if "%~1"=="" pause
echo %* | findstr /C:"--noelevate" >nul && pause
exit /b 0

:: --- uninstall: removes all install artefacts unconditionally -------
:: Elevation, if needed, was handled by the top-level check.
:uninstall
echo Removing all install artefacts...
taskkill /F /IM "%EXE_NAME%" >nul 2>&1
if exist "%STARTUP_VBS%"        del /F /Q "%STARTUP_VBS%"
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
if exist "%LOCAL_DEST%"         rmdir /S /Q "%LOCAL_DEST%"
if exist "%PROGRAMFILES_DEST%"  rmdir /S /Q "%PROGRAMFILES_DEST%"
echo(
echo [OK] Uninstalled.
:: Pause if invoked interactively (no args) or via the elevated re-launch
:: (so the freshly-popped UAC console doesn't vanish before the user
:: sees the result).
if "%~1"=="" pause
echo %* | findstr /C:"--noelevate" >nul && pause
exit /b 0

:: Embedded zephyrus-g14-fn-nav.exe (base64; inserted by package.py)
::PAYLOAD_START
{PAYLOAD_BASE64}
::PAYLOAD_END

:: Embedded task.xml for mode 3 (base64; inserted by package.py)
::TASK_XML_START
{TASK_XML_BASE64}
::TASK_XML_END
'''


TASK_XML = '''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <GroupId>S-1-5-32-545</GroupId>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>Parallel</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>wscript.exe</Command>
      <Arguments>"C:\\Program Files\\zephyrus-g14-fn-nav\\start.vbs"</Arguments>
    </Exec>
  </Actions>
</Task>
'''


def _pem_wrap(b64: str) -> str:
    lines = ["-----BEGIN CERTIFICATE-----"]
    lines += [b64[i:i + 76] for i in range(0, len(b64), 76)]
    lines.append("-----END CERTIFICATE-----")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exe", required=True, help="Path to built .exe")
    p.add_argument("--version", default="dev", help="Version string for banner / output filename")
    p.add_argument("--output", default=None, help="Output .bat path (default: derived from --version)")
    args = p.parse_args()

    exe = Path(args.exe)
    if not exe.is_file():
        print(f"[ERROR] {exe} not found", file=sys.stderr)
        return 1

    exe_data = exe.read_bytes()
    exe_payload = _pem_wrap(base64.b64encode(exe_data).decode("ascii"))

    # Task XML must be UTF-16 LE with BOM (Task Scheduler requires it)
    xml_bytes = TASK_XML.encode("utf-16-le")
    xml_bytes = b"\xff\xfe" + xml_bytes  # prepend BOM
    xml_payload = _pem_wrap(base64.b64encode(xml_bytes).decode("ascii"))

    bat = (
        INSTALLER_TEMPLATE
        .replace("{APP_VERSION}", args.version)
        .replace("{PAYLOAD_BASE64}", exe_payload)
        .replace("{TASK_XML_BASE64}", xml_payload)
    )

    if args.output:
        out = Path(args.output)
    elif args.version != "dev":
        out = Path(f"install-zephyrus-g14-fn-nav-v{args.version}.bat")
    else:
        out = Path("install.bat")

    out.write_text(bat, encoding="ascii", newline="\r\n")
    print(
        f"Wrote {out} ({out.stat().st_size:,} bytes; "
        f"embedded {len(exe_data):,} byte exe + {len(xml_bytes):,} byte task XML)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Package zephyrus-g14-fn-nav.exe into a self-extracting install.bat.

The output .bat embeds the binary as base64 (PEM-style 76-char wrapping)
between ::PAYLOAD_START / ::PAYLOAD_END markers and extracts it at
runtime via certutil -decode. Same .bat handles install + uninstall +
status; same auto-start mechanism (Scheduled Task at user logon, hidden
via a tiny VBS launcher) as documented in
docs/adr/0008-scheduled-task-not-windows-service.md.
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
    echo         Example: install-zephyrus-g14-fn-nav.bat
    pause
    exit /b 1
)

set "DEST=%LOCALAPPDATA%\zephyrus-g14-fn-nav"
set "EXE_NAME=zephyrus-g14-fn-nav.exe"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "STARTUP_VBS=%STARTUP_DIR%\zephyrus-g14-fn-nav.vbs"
set "TEMP_DIR=%TEMP%\zephyrus-g14-fn-nav-%RANDOM%"

echo === zephyrus-g14-fn-nav installer v{APP_VERSION} ===
echo(

:: Argument dispatch
if "%~1"=="--install"   goto :install
if "%~1"=="--uninstall" goto :uninstall
if "%~1"=="--status"    goto :status

:: No args: show status with interactive menu
:status
set "INSTALLED=0"
if exist "%DEST%\%EXE_NAME%" set "INSTALLED=1"

if "%INSTALLED%"=="1" (
    echo Status: INSTALLED at %DEST%
    if "%~1"=="--status" exit /b 0
    echo(
    echo [1] Uninstall
    echo [2] Cancel
    echo(
    set /p "CHOICE=Select: "
    if "!CHOICE!"=="1" goto :uninstall
    echo Cancelled.
    pause
    exit /b 0
) else (
    echo Status: NOT INSTALLED
    if "%~1"=="--status" exit /b 0
    echo(
    echo [1] Install
    echo [2] Cancel
    echo(
    set /p "CHOICE=Select: "
    if "!CHOICE!"=="1" goto :install
    echo Cancelled.
    pause
    exit /b 0
)

:install
:: Stop any existing instance before overwriting the .exe
taskkill /F /IM "%EXE_NAME%" >nul 2>&1

if not exist "%DEST%" mkdir "%DEST%"
if not exist "%STARTUP_DIR%" mkdir "%STARTUP_DIR%"
mkdir "%TEMP_DIR%" 2>nul

:: Extract the embedded base64 payload between markers (same idiom as the
:: Daslight reference installer). Disable delayed expansion so '!' chars
:: in base64 lines don't get expanded.
set "B64_FILE=%TEMP_DIR%\payload.b64"
setlocal disabledelayedexpansion
set "FOUND="
(for /f "usebackq tokens=*" %%L in ("%~f0") do (
    if defined FOUND (
        if "%%L"=="::PAYLOAD_END" goto :decode
        echo %%L
    )
    if "%%L"=="::PAYLOAD_START" set "FOUND=1"
)) > "%B64_FILE%"
:decode
endlocal

:: Decode to the install directory
certutil -decode "%TEMP_DIR%\payload.b64" "%DEST%\%EXE_NAME%" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] certutil -decode failed.
    rmdir /S /Q "%TEMP_DIR%" 2>nul
    pause
    exit /b 1
)
if not exist "%DEST%\%EXE_NAME%" (
    echo [ERROR] Payload extraction failed.
    rmdir /S /Q "%TEMP_DIR%" 2>nul
    pause
    exit /b 1
)

:: Write the hidden-window VBS launcher directly into the Startup folder.
:: Windows runs .vbs files in the Startup folder at every user logon
:: (no Scheduled Task, no admin / UAC).
> "%STARTUP_VBS%" echo Set sh = CreateObject("WScript.Shell")
>> "%STARTUP_VBS%" echo sh.Run """%DEST%\%EXE_NAME%""", 0, False

:: Cleanup temp
rmdir /S /Q "%TEMP_DIR%" 2>nul

:: Start it now so the user doesn't need to log out
wscript.exe "%STARTUP_VBS%"

echo(
echo [OK] Installed. Listener will auto-start at every logon.
echo      Binary: %DEST%\%EXE_NAME%
echo      Autostart: %STARTUP_VBS%
if "%~1"=="" pause
exit /b 0

:uninstall
echo Stopping listener and removing autostart entry...
taskkill /F /IM "%EXE_NAME%" >nul 2>&1
if exist "%STARTUP_VBS%" del /F /Q "%STARTUP_VBS%"
if exist "%DEST%" rmdir /S /Q "%DEST%"
echo(
echo [OK] Uninstalled.
if "%~1"=="" pause
exit /b 0

:: Embedded zephyrus-g14-fn-nav.exe (base64; inserted by package.py)
::PAYLOAD_START
{PAYLOAD_BASE64}
::PAYLOAD_END
'''


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exe", required=True, help="Path to built .exe")
    p.add_argument("--version", default="dev", help="Version string for the banner / output filename")
    p.add_argument("--output", default=None, help="Output .bat path (default: derived from --version)")
    args = p.parse_args()

    exe = Path(args.exe)
    if not exe.is_file():
        print(f"[ERROR] {exe} not found", file=sys.stderr)
        return 1

    data = exe.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")

    # PEM 76-char wrapping; certutil -decode expects this envelope
    lines = ["-----BEGIN CERTIFICATE-----"]
    lines += [b64[i:i + 76] for i in range(0, len(b64), 76)]
    lines.append("-----END CERTIFICATE-----")
    payload = "\n".join(lines)

    bat = (
        INSTALLER_TEMPLATE
        .replace("{APP_VERSION}", args.version)
        .replace("{PAYLOAD_BASE64}", payload)
    )

    if args.output:
        out = Path(args.output)
    elif args.version != "dev":
        out = Path(f"install-zephyrus-g14-fn-nav-v{args.version}.bat")
    else:
        out = Path("install.bat")

    out.write_text(bat, encoding="ascii", newline="\r\n")
    print(f"Wrote {out} ({out.stat().st_size:,} bytes; embedded {len(data):,} byte exe)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

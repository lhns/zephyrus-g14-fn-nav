# 9. Distribute via a single self-extracting `.bat` with embedded base64-encoded binary

Date: 2026-05-07

## Status

Accepted.

## Context

Two ways to deliver a release:

1. **Side-by-side**: ship `zephyrus-g14-fn-nav.exe` and a separate
   `install.bat` as two release assets. The .bat references the
   adjacent .exe.
2. **Self-extracting**: embed the .exe inside the .bat as base64 between
   marker comments and decode it at runtime via `certutil -decode`. One
   release asset.

Pattern (2) is modelled after a reference installer the user provided
(`C:\Users\pierr\Downloads\install-daslight-shim-v1.4.1.bat`, built by
the sibling `package.py`). The marker idiom — `::PAYLOAD_START` /
`::PAYLOAD_END` framing a `-----BEGIN/END CERTIFICATE-----` PEM block —
is the canonical way to do self-extracting `.bat` files on Windows
without external tooling: `certutil` is a system-included utility on
every supported Windows version.

## Decision

Use pattern (2). One artefact per Release:
`install-zephyrus-g14-fn-nav-vX.Y.Z.bat`. The user downloads one file,
double-clicks, picks Install or Uninstall from the interactive menu (or
runs with `--install` / `--uninstall` / `--status` flags).

`scripts/package.py` is a Python builder. It holds the entire `.bat`
template inline as a triple-quoted raw string (single source of truth —
no separate `.template` file to drift), base64-encodes the .exe in PEM
format (76-char lines, BEGIN/END CERTIFICATE markers), and writes the
output `.bat` with **CRLF line endings + ASCII encoding** so `cmd.exe`
parses it cleanly.

The CI workflow runs the packager only on `release: published` events
and uploads the resulting versioned `.bat` as the sole release asset.
The loose `.exe` continues to be uploaded as a per-commit workflow
artifact for contributors who want a fast prebuilt without extracting.

## Consequences

- **Best end-user UX:** download one file, run it. No "drop these two
  files in the same folder" instructions.
- **Artefact size grows ~40%:** ~180 KB binary becomes ~250 KB .bat
  after base64 (4/3 expansion + script overhead). Fine for a hobby tool.
- **SmartScreen warning on first run:** unavoidable without code
  signing; the same warning would appear on a loose .exe. Documented in
  the README.
- **Antivirus heuristics** sometimes flag self-extracting `.bat`
  installers. If this becomes a real problem in practice, switch to
  side-by-side delivery — the loose .exe is already on the workflow
  artifact path, so the fallback is one workflow change away.
- **Filename guard required:** browsers append `(1)`, `(2)` to
  re-downloaded files. Unmatched parens break `cmd.exe`'s block parser.
  The installer rejects parenthesised filenames up front with a clear
  error. Carried over from the reference installer — non-obvious bug
  worth keeping the guard for.

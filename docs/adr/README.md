# Architecture Decision Records

Each file documents one decision: the context that produced it, the choice
made, and the consequences. ADRs are append-only; if a decision changes,
write a new ADR that supersedes the old one rather than rewriting history.

| #    | Title                                                            | Status   |
| ---- | ---------------------------------------------------------------- | -------- |
| 0001 | [Listen via the ASUS HID interface, not a Windows keyboard hook](0001-listen-via-hid-instead-of-keyboard-hook.md) | Accepted |
| 0002 | [Rust for the production listener](0002-rust-for-the-listener.md) | Accepted |
| 0003 | [SendInput with `KEYEVENTF_EXTENDEDKEY`](0003-sendinput-with-extendedkey-flag.md) | Accepted |
| 0004 | [Hard-code Fn+arrow mapping in v1; defer `config.toml`](0004-hardcoded-mapping-no-config-yet.md) | Accepted |
| 0005 | [No client-side auto-repeat in v1](0005-no-auto-repeat-in-v1.md) | Accepted |
| 0006 | [Fn+Up/Down emits PgUp/PgDn + restores brightness; Ctrl+Fn+Up/Down is the only intentional brightness control](0006-fn-updown-pgup-and-brightness-restore.md) | Accepted |
| 0007 | [Track keyboard brightness as in-process state, not by reading from hardware](0007-state-tracking-for-brightness.md) | Accepted |
| 0008 | [Auto-start via the Startup folder, not a Windows Service or Scheduled Task](0008-startup-folder-not-windows-service.md) | Accepted |
| 0009 | [Distribute via a single self-extracting `.bat` with embedded base64-encoded binary](0009-self-extracting-bat-installer.md) | Accepted |

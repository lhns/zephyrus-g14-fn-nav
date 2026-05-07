//! Background HID listener for ASUS Zephyrus G14 (GA401L).
//!
//! Watches the ASUS-specific HID interface for Fn+arrow vendor codes and
//! synthesises navigation keys (Home/End/PgUp/PgDn) via Win32 SendInput.
//!
//! Fn+Up/Down also commands the EC firmware to bump keyboard backlight
//! brightness — we cannot suppress that, so we restore brightness to a
//! tracked target value after each PgUp/PgDn. Ctrl+Fn+Up/Down is reclaimed
//! as the only intentional brightness adjustment.

use std::process::ExitCode;

use hidapi::{HidApi, HidDevice};
use windows::Win32::UI::Input::KeyboardAndMouse::{
    GetAsyncKeyState, SendInput, INPUT, INPUT_0, INPUT_KEYBOARD, KEYBDINPUT,
    KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, VIRTUAL_KEY, VK_CONTROL, VK_END, VK_HOME, VK_NEXT,
    VK_PRIOR,
};

const ASUS_VID: u16 = 0x0B05;
const KB_PID: u16 = 0x1866;
/// Path fragment that identifies the ASUS-specific Fn-combo HID collection.
const TARGET_PATH_FRAGMENT: &str = "mi_02&col01";

/// Report ID used by the ASUS Fn-combo channel (input *and* output).
const ASUS_REPORT_ID: u8 = 0x5A;

/// Heartbeat / keepalive code on the same channel — ignore.
const HEARTBEAT: u8 = 0xEC;

// Vendor action codes captured during Stage 1 diagnostic. See docs/codes.md.
const FN_LEFT: u8 = 0xB2;
const FN_RIGHT: u8 = 0xB3;
const FN_UP: u8 = 0xC4;
const FN_DOWN: u8 = 0xC5;

const MAX_BRIGHTNESS: u8 = 3;
/// Default brightness assumption when the listener launches. Matches the
/// typical state of the laptop right after boot (backlight off). If the
/// user's actual level differs, the first plain Fn+Up/Down will snap to
/// this value (one visible step); after that, target == actual.
const DEFAULT_BRIGHTNESS: u8 = 0;

fn open_target(api: &HidApi) -> Result<HidDevice, String> {
    let target = api
        .device_list()
        .find(|d| {
            d.vendor_id() == ASUS_VID
                && d.product_id() == KB_PID
                && d.path()
                    .to_string_lossy()
                    .to_lowercase()
                    .contains(TARGET_PATH_FRAGMENT)
        })
        .ok_or_else(|| {
            format!(
                "no HID device matching VID=0x{:04X} PID=0x{:04X} path~'{}'",
                ASUS_VID, KB_PID, TARGET_PATH_FRAGMENT
            )
        })?;

    let path = target.path().to_owned();
    api.open_path(&path)
        .map_err(|e| format!("failed to open device: {e}"))
}

fn ctrl_held() -> bool {
    // GetAsyncKeyState: high bit set when key is currently down.
    unsafe { (GetAsyncKeyState(VK_CONTROL.0 as i32) as u16) & 0x8000 != 0 }
}

fn send_key(vk: VIRTUAL_KEY) {
    let down = INPUT {
        r#type: INPUT_KEYBOARD,
        Anonymous: INPUT_0 {
            ki: KEYBDINPUT {
                wVk: vk,
                wScan: 0,
                dwFlags: KEYEVENTF_EXTENDEDKEY,
                time: 0,
                dwExtraInfo: 0,
            },
        },
    };
    let up = INPUT {
        r#type: INPUT_KEYBOARD,
        Anonymous: INPUT_0 {
            ki: KEYBDINPUT {
                wVk: vk,
                wScan: 0,
                dwFlags: KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP,
                time: 0,
                dwExtraInfo: 0,
            },
        },
    };
    let inputs = [down, up];
    unsafe {
        SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);
    }
}

/// Write the keyboard-brightness command. Byte sequence verified against
/// G-Helper's `Aura.DirectBrightness` in `seerge/g-helper`. Sent as a HID
/// **feature** report (G-Helper uses `SetFeature`); plain output writes
/// fail with ERROR_INVALID_FUNCTION on this device.
fn aura_set_brightness(device: &HidDevice, level: u8) {
    let level = level.min(MAX_BRIGHTNESS);
    let report = [ASUS_REPORT_ID, 0xBA, 0xC5, 0xC4, level];
    if let Err(e) = device.send_feature_report(&report) {
        eprintln!("aura_set_brightness({level}) failed: {e}");
    }
}

fn run() -> Result<(), String> {
    let api = HidApi::new().map_err(|e| format!("hidapi init failed: {e}"))?;
    let device = open_target(&api)?;

    println!(
        "g14-fn-nav: listening on ASUS HID (VID 0x{:04X} PID 0x{:04X}, {})",
        ASUS_VID, KB_PID, TARGET_PATH_FRAGMENT
    );

    // Don't touch brightness at startup — leave whatever level the user
    // had. target_brightness defaults to DEFAULT_BRIGHTNESS (off, matching
    // typical post-boot state). If the user's actual level is different,
    // the first plain Fn+Up/Down will snap to it (one visible step);
    // after that, target == actual and restores are invisible. ADR 0007.
    let mut target_brightness: u8 = DEFAULT_BRIGHTNESS;

    let mut buf = [0u8; 16];
    loop {
        let len = device
            .read(&mut buf)
            .map_err(|e| format!("hid read failed: {e}"))?;
        if len < 2 {
            continue;
        }
        if buf[0] != ASUS_REPORT_ID {
            continue;
        }

        let action_code = buf[1];
        if action_code == 0x00 || action_code == HEARTBEAT {
            continue;
        }

        match action_code {
            FN_LEFT => send_key(VK_HOME),
            FN_RIGHT => send_key(VK_END),

            FN_UP if ctrl_held() => {
                // Intentional brightness up. EC has already bumped; just
                // track it.
                target_brightness = (target_brightness + 1).min(MAX_BRIGHTNESS);
                println!("Ctrl+Fn+Up -> brightness target = {target_brightness}");
            }
            FN_UP => {
                send_key(VK_PRIOR);
                aura_set_brightness(&device, target_brightness);
            }

            FN_DOWN if ctrl_held() => {
                target_brightness = target_brightness.saturating_sub(1);
                println!("Ctrl+Fn+Down -> brightness target = {target_brightness}");
            }
            FN_DOWN => {
                send_key(VK_NEXT);
                aura_set_brightness(&device, target_brightness);
            }

            other => {
                println!("Fn-code 0x{other:02X} -> unmapped");
            }
        }
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}

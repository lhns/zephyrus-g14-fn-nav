"""ASUS HID diagnostic.

Opens every HID interface with USB vendor ID 0x0B05 (ASUS) and prints every
incoming raw report. Use to discover which Fn+key combos emit codes that
reach Windows.

Run as Administrator. Optionally write output to a log file with --log PATH.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

from pywinusb import hid

ASUS_VID = 0x0B05


def short_id(device) -> str:
    """Compact device tag, e.g. 'VID_0B05 PID_1866 MI_02 COL01'."""
    path = device.device_path or ""
    parts = path.upper().split("#")
    if len(parts) < 2:
        return path
    return parts[1].replace("&", " ")


def make_handler(device, log_fp):
    label = short_id(device)

    def handler(data: list[int]) -> None:
        ts = dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        report_id = data[0] if data else 0
        payload = " ".join(f"{b:02X}" for b in data[1:]) if len(data) > 1 else ""
        line = f"{ts}  {label}  rpt=0x{report_id:02X}  [{payload}]"
        print(line)
        if log_fp:
            log_fp.write(line + "\n")
            log_fp.flush()

    return handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, help="Append output to this file")
    args = parser.parse_args()

    log_fp = None
    if args.log:
        log_fp = open(args.log, "a", encoding="utf-8")
        log_fp.write(f"\n=== session start {dt.datetime.now().isoformat()} ===\n")
        log_fp.flush()

    devices = hid.HidDeviceFilter(vendor_id=ASUS_VID).get_devices()
    if not devices:
        print(f"No HID devices found with VID 0x{ASUS_VID:04X}.")
        return 1

    print(f"Found {len(devices)} ASUS HID device(s):")
    for d in devices:
        print(f"  - {short_id(d)}  ({d.product_name!r})")
    print()
    print("Opening...")

    opened = []
    for d in devices:
        try:
            d.open()
            d.set_raw_data_handler(make_handler(d, log_fp))
            opened.append(d)
            print(f"  [open]  {short_id(d)}")
        except Exception as exc:
            print(f"  [skip]  {short_id(d)}  -> {exc}")

    if not opened:
        print("\nCould not open any device. Try running as Administrator.")
        return 1

    print()
    print("Listening. Each line below is one raw HID report.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        for d in opened:
            try:
                d.close()
            except Exception:
                pass
        if log_fp:
            log_fp.write(f"=== session end {dt.datetime.now().isoformat()} ===\n")
            log_fp.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())

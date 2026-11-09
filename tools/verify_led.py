#!/usr/bin/env python3
"""Compare an owner's L5 conversion directly with a locally supplied wpclp 1.4.

Default-delay V2 only. All images and raw tool logs stay in the private output
folder. The JSON summary contains identities/counts, never driver bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kh5patch.core import checksum, convert, identity
from kh5patch.led import transform


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--wpclp', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    baseline = args.baseline.resolve()
    original = baseline.read_bytes()
    kh5, _ = convert(original)  # Exact official baseline and qualified KH5 hashes.
    folder = args.output.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    reference_file = folder / 'PRIVATE-wpclp-led-only.bin'
    tool = args.wpclp.resolve()
    # T-1 is only a reference label; it does not affect the lamp-driver patch.
    result = subprocess.run([str(tool), str(baseline), str(reference_file)],
                            input='T-1\n', text=True, capture_output=True,
                            timeout=30, cwd=folder)
    (folder / 'PRIVATE-wpclp.log').write_text(result.stdout + result.stderr)
    if result.returncode or 'Updated ROM Validation Passed!' not in result.stdout:
        raise RuntimeError('wpclp failed; preserve and inspect the private log')
    if 'version 1.4' not in result.stdout or 'FOUND Lamp Driver V2 Signature' not in result.stdout:
        raise RuntimeError('Expected wpclp 1.4 supported V2 driver')
    reference = reference_file.read_bytes()
    local_led = transform(original)
    local_t1 = bytearray(local_led)
    local_t1[0x70D5C] = ord('T')
    local_t1 = checksum(local_t1, revision=1)
    # Compare the complete reference image, not just the positions we edit.
    if local_t1 != reference:
        raise AssertionError('Whole LED-only image differs from upstream wpclp')
    start, end = 0x7DCF5, 0x7DD80
    if kh5[start:end] != reference[start:end]:
        raise AssertionError('Qualified KH5 lamp-driver bytes differ from wpclp')
    if baseline.read_bytes() != original:
        raise AssertionError('Input baseline was modified')
    summary = dict(
        result='PASS', baseline=identity(original), kh5=identity(kh5),
        wpclp_version='1.4', wpclp_options='default delay; no -e; reference label T-1',
        wpclp_executable_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),
        reference_image=identity(reference), whole_led_only_image_identical=True,
        kh5_lamp_driver_identical=True,
        lamp_driver_comparison=dict(start_inclusive='7DCF5', end_exclusive='7DD80',
                                    bytes=end-start, differing_bytes=0,
                                    sha256=hashlib.sha256(reference[start:end]).hexdigest()),
        led_changed_bytes=sum(a != b for a, b in zip(original, local_led)),
        input_unchanged=True,
        scope='Byte equivalence to wpclp default V2; no physical LED test')
    (folder / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()

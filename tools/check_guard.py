#!/usr/bin/env python3
"""6809 execution test of the L-5/L-5C multiball entry; destroys emulator state.

This isolates the entry's guard, not a gameplay regression. IRQs are masked and
the main CPU runs to either the original continuation or a sentinel return.
Use a unit-only image containing the bootstrap; never burn that image.
"""
import argparse
import hashlib
import json
import pathlib
import time
import urllib.parse
import urllib.request


def main():
    p = argparse.ArgumentParser()
    p.add_argument("image", type=pathlib.Path)
    p.add_argument("--expect", choices=["original", "guarded"], required=True)
    p.add_argument("--port", type=int, default=8935)
    p.add_argument("--log", type=pathlib.Path, required=True)
    p.add_argument("--task-states", action="store_true", help="also test native scheduler lookup with F2 pending and F3 running")
    args = p.parse_args()
    image = args.image.read_bytes()
    evidence = {"image": str(args.image), "sha1": hashlib.sha1(image).hexdigest(),
                "kind": "isolated 6809 entry guard execution; not gameplay",
                "temporary_emulator_bootstrap": {"address": "FB40", "hex": "862AB73FFCCC12347E6091"},
                "cases": []}

    def api(path, **params):
        url = f"http://127.0.0.1:{args.port}/api/{path}?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.load(response)
        if data.get("status") == "error":
            raise ValueError(data)
        return data

    def write(addr, data):
        api("debugger/memory/write", addr=f"{addr:04X}", data=bytes(data).hex())

    def reg(name, val):
        api("debugger/state/write", reg=name, val=f"{val:X}")

    api("debugger/control", cmd="pause")
    api("debugger/breakpoints", cmd="clear")
    api("debugger/watchpoints", cmd="clear")
    loaded = api("debugger/memory", addr="6091", bank="2A", size=5)["data"]
    assert bytes(loaded) == image[0x2A091:0x2A096], "Loaded entry differs from specified image"
    loaded = api("debugger/memory", addr="6F98", bank="2A", size=28)["data"]
    assert bytes(loaded) == image[0x2AF98:0x2AFB4], "Loaded trampoline differs from specified image"
    for addr in ["6096", "7FFF"]:
        api("debugger/breakpoints", cmd="add", addr=addr, bank="2A")
    bootstrap = bytes.fromhex("86 2A B7 3F FC CC 12 34 7E 60 91")
    assert image[0x7FB40:0x7FB4B] == bootstrap, "Use a unit-only image with the bootstrap installed"
    # WPC's executable opcode mapping differs from its RAM data mapping.
    # The unit-only image uses previously unused fixed-ROM bytes for the bootstrap.
    # The bootstrap is excluded from the playable game build.
    assert bytes(api("debugger/memory", addr="FB40", size=11)["data"]) == bootstrap
    for task_id in ([0, 0xF2, 0xF3] if args.task_states else [None]):
        for qualified in range(4):
            for live in range(4):
                if task_id is not None:
                    # Two native scheduler list heads, one inert synthetic record.
                    write(0x0366, [0x0D, 0] if task_id else [0, 0])
                    write(0x0371, [0, 0])
                    write(0x0059, [0, 0])
                    write(0x0D00, [0]*0x2D)
                    write(0x0D11, [0, task_id])
                write(0x008C, [0, 0, 0])
                write(0x17A4, [0])
                write(0x0805, [qualified, live])
                # $0000-$0FFF is writable before the ROM has configured CMOS
                # protection. Keep the synthetic stack in that unprotected range.
                write(0x0F00, [0x7F, 0xFF])
                # Switch banks through an actual 6809 STA, then load D and jump.
                # A debugger write of the ASIC register is not an execution test.
                for name, val in [("CC", 0x50), ("DP", 0), ("S", 0x0F00), ("PC", 0xFB40)]:
                    reg(name, val)
                api("debugger/control", cmd="resume")
                deadline = time.monotonic() + 5
                while not api("info")["paused"]:
                    if time.monotonic() > deadline:
                        raise TimeoutError("No guard continuation/return breakpoint hit")
                    time.sleep(0.001)
                cpu = api("debugger/state")["cpus"][0]
                allow = args.expect == "original" or (qualified > 0 and live == 1 and task_id != 0xF2)
                expected_pc = 0x6096 if allow else 0x7FFF
                case = {"synthetic_task_id": task_id, "ram_0805": qualified, "ram_0806": live, "expected_pc": expected_pc,
                        "cpu": cpu, "pass": cpu["pc"] == expected_pc and cpu["a"] == 0x12 and cpu["b"] == 0x34
                        and cpu["sp"] == (0x0EFE if allow else 0x0F02)}
                evidence["cases"].append(case)
                args.log.write_text(json.dumps(evidence, indent=2) + "\n")
                if not case["pass"]:
                    raise AssertionError(case)
    print(f"PASS: {len(evidence['cases'])} 6809 guard cases; D and stack preserved.")


if __name__ == "__main__":
    main()

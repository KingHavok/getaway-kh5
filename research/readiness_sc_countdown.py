"""Port of authored historical controller readiness_sc_countdown. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import json

import pathlib

from readiness_session import session, configure, launch_and_validate

def run_case(folder, port, value):
    with session(folder, port, __file__) as (api, result):
        api.frames(1200)
        configure(api, {0x1B1F: 5, 0x1B23: 0, 0x1B39: 3, 0x1B43: 0,
                        0x1B51: 1, 0x1B5F: 0, 0x1B61: 0, 0x1B9D: 1,
                        0x1BBF: 0, 0x1BC9: 0, 0x1BCB: 20, 0x1BD5: value})
        api.call('debugger/tracepoints', cmd='clear')
        for addr in ['44E1', '4512', '4520', '4530']:
            api.call('debugger/tracepoints', cmd='add', addr=addr, bank='2A')
        api.button('200', after=300)
        launch_and_validate(api)
        for _ in range(24):
            if api.state()['gears'][0] == 4:
                break
            api.pulse(4, '12', after=180)
            api.pulse(4, '400', on=12, after=180)
        assert api.state()['gears'][0] == 4, 'Could not reach fourth gear naturally'
        for _ in range(6):
            state = api.state(tasks=True)
            if 0xB7 in state['task_ids']:
                break
            api.pulse(4, '12', after=180)
        state = api.wait('native Supercharger Mode task', lambda s: 0xB7 in s['task_ids'], tasks=True, limit=900)
        samples = []
        for _ in range(value * 3 + 30):
            state = api.state(tasks=True)
            counter = api.memory(0x8D4, 1)[0]
            samples.append({'frame': api.frames_run, 'counter': counter, 'mode_task_present': 0xB7 in state['task_ids']})
            if not counter and 0xB7 not in state['task_ids']:
                break
            # Keep real playfield activity going, without making a Supercharger
            # shot that could change/extend the countdown.
            api.pulse(4, '12', after=54)
        else:
            raise TimeoutError('Native countdown did not finish within bounded observation')
        api.frames(600)
        api.pulse(4, '400', on=12, after=180)
        final = api.wait('can shift after timed mode', lambda s: s['gears'][0] == 5, limit=900)
        traces = api.call('debugger/tracepoints')['log']
        assert len(traces) < 512
        starts = [t for t in traces if t['pc'] == 0x44E1]
        decrements = [t for t in traces if t['pc'] == 0x4520]
        exits = [t for t in traces if t['pc'] == 0x4530]
        assert len(starts) == len(exits) == 1
        assert bytes.fromhex(starts[0]['ram'])[0x8D4] == value
        assert [bytes.fromhex(t['ram'])[0x8D4] for t in decrements] == list(range(value, 0, -1))
        assert bytes.fromhex(exits[0]['ram'])[0x8D4] == 0
        first_tick = next(t for t in traces if t['pc'] == 0x4512)
        elapsed = exits[0]['time'] - first_tick['time']
        assert .5 * value < elapsed < 2 * value
        (folder / 'traces.json').write_text(json.dumps({'log': traces}, indent=2) + '\n')
        result.update(result='PASS', supercharger_timer_setting=value, getaway_timer_setting=20,
                      countdown_decrements=len(decrements), countdown_elapsed_emulated_seconds=elapsed,
                      samples=samples, final=final, frames=api.frames_run,
                      limitations=['Measures native countdown and termination, not equality of UI seconds to wall-clock seconds',
                                   'No Supercharger shots during countdown; extension/paused-ball cases remain separate',
                                   'Getaway timer and output pulse timing are not covered'])
    return result
from lab.config import REPO as ROOT

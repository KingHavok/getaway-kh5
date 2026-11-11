"""Port of authored historical controller readiness_getaway_countdown. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import json

import pathlib

from readiness_session import session, configure, qualify_locks, collect_lock

from readiness_multiplayer import ensure_playable, wait_saver

def run_case(folder, port, value):
    with session(folder, port, __file__) as (api, result):
        api.frames(1200)
        configure(api, {0x1B1F: 5, 0x1B23: 0, 0x1B39: 3, 0x1B43: 0,
                        0x1B51: 1, 0x1B5F: 0, 0x1B61: 0, 0x1B9D: 1,
                        0x1BBF: 0, 0x1BC9: 0, 0x1BCB: value, 0x1BD5: 20})
        api.call('debugger/tracepoints', cmd='clear')
        for addr in ['5AC3', '471B', '4750', '4755', '475C', '6253']:
            api.call('debugger/tracepoints', cmd='add', addr=addr, bank='2A')
        api.button('200', after=300)
        ensure_playable(api)
        qualify_locks(api)
        for credit in range(1, 4):
            collect_lock(api, credit)
            if credit < 3:
                ensure_playable(api)
        api.wait('ordinary multiball', lambda s: s['live'] == 3, limit=2400)
        api.frames(600)
        wait_saver(api)
        for _ in range(2):
            api.pulse(5, '2000', after=300)
        api.wait('single ball after multiball', lambda s: s['live'] == 1, limit=1200)
        samples = []
        for _ in range(2 * value + 30):
            state = api.state(tasks=True)
            counter = api.memory(0x874, 1)[0]
            samples.append({'frame': api.frames_run, 'counter': counter, 'task_ids': state['task_ids']})
            if counter == 0 and 0xF7 not in state['task_ids'] and 0x89 not in state['task_ids']:
                break
            # A real slingshot switch provides activity without collecting the
            # last-chance jackpot or putting a ball inside the Supercharger.
            api.call('input', sw=31, val=1)
            api.frames(6)
            api.call('input', sw=31, val=0)
            api.frames(54)
        else:
            raise TimeoutError('Getaway Time did not terminate')
        final = api.state(tasks=True)
        assert (final['player'], final['ball'], final['live'], final['phase']) == (1, 1, 1, [0, 0, 0])
        traces = api.call('debugger/tracepoints')['log']
        assert len(traces) < 512
        starts = [t for t in traces if t['pc'] == 0x5AC3]
        ticks = [t for t in traces if t['pc'] == 0x4750]
        expires = [t for t in traces if t['pc'] == 0x4755]
        cleanups = [t for t in traces if t['pc'] == 0x475C]
        assert len(starts) == len(expires) == len(cleanups) == 1
        assert starts[0]['a'] == value
        assert [bytes.fromhex(t['ram'])[0x874] for t in ticks] == list(range(value, 0, -1))
        assert bytes.fromhex(expires[0]['ram'])[0x874] == 0
        begin = next(t for t in traces if t['pc'] == 0x471B)
        elapsed = expires[0]['time'] - begin['time']
        assert .5 * value < elapsed < 2 * value
        assert sum(t['pc'] == 0x6253 for t in traces) == 1, 'Unexpected multiball restart'
        for address, expected in [(0x1BCB, value), (0x1BD5, 20)]:
            assert int.from_bytes(api.memory(address, 2), 'big') == expected
        (folder / 'traces.json').write_text(json.dumps({'log': traces}, indent=2) + '\n')
        result.update(result='PASS', getaway_timer_setting=value, supercharger_timer_setting=20,
                      countdown_decrements=len(ticks), countdown_elapsed_emulated_seconds=elapsed,
                      samples=samples, final=final, frames=api.frames_run,
                      limitations=['Ordinary MB without jackpot followed by an uncollected Getaway Time expiry only',
                                   'No pause, extension, last-second collection, Redline or tilt/restart timing inferred',
                                   'Native countdown measured; UI seconds are not asserted equal to wall-clock seconds'])
    return result
from lab.config import REPO as ROOT

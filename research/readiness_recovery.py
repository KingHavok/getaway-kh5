"""Port of authored historical controller readiness_recovery. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import json

import pathlib

from readiness_games import ROOT

from readiness_session import session, configure, launch_and_validate, qualify_locks, collect_lock

def run_case(folder, port, locks, search_stage):
    with session(folder, port, __file__) as (api, result):
        api.frames(1200)
        configure(api, {0x1B1F: 5, 0x1B23: 0, 0x1B39: 3, 0x1B43: 0,
                        0x1B51: 1, 0x1B61: 0, 0x1B9D: 1, 0x1BBF: 0, 0x1BC9: 0})
        api.call('debugger/tracepoints', cmd='clear')
        for addr, bank in [('481A', '30'), ('484C', '30'), ('6253', '2A'), ('6A88', '2A')]:
            api.call('debugger/tracepoints', cmd='add', addr=addr, bank=bank)
        api.call('monitor', cmd='clear')
        for coil in [2, 3, 4, 7, 11, 12]:
            api.call('monitor', cmd='add', type='sol', id=coil)
        api.button('200', after=300)
        launch_and_validate(api)
        qualify_locks(api)
        for count in range(1, locks + 1):
            collect_lock(api, count)
            launch_and_validate(api)
        api.wait('saver expired before missing-ball scenario',
                 lambda s: not ({0xE2, 0xE3, 0xF2} & set(s['task_ids'])),
                 limit=2400, step=60, tasks=True, activity=True)
        initial = api.state()
        assert initial['lock_credits'][0] == locks and initial['live'] == 1
        assert sum(initial['switches'][n] for n in [74, 75, 76]) == locks
        # Start a clean observation window after setup and saver expiry.
        api.call('debugger/tracepoints', cmd='clear')
        for addr, bank in [('481A', '30'), ('484C', '30'), ('6253', '2A'), ('6A88', '2A')]:
            api.call('debugger/tracepoints', cmd='add', addr=addr, bank=bank)
        start_frame = api.frames_run
        for _ in range(180):
            api.frames(60)
            traces = api.call('debugger/tracepoints')['log']
            if any(t['pc'] == 0x481A and t['bank'] == 0x30 and t['a'] >= search_stage for t in traces):
                search_frame = api.frames_run
                break
        else:
            raise TimeoutError('Ball search did not reach requested native stage')
        missing = api.state()
        assert (missing['player'], missing['ball']) == (1, 1)
        assert not any(t['pc'] in [0x6253, 0x6A88] and t['bank'] == 0x2A for t in traces)
        # The missing ball returns to a real playfield switch through the simulator.
        api.pulse(4, '12', after=180)
        calls_after_return = sum(t['pc'] == 0x481A and t['bank'] == 0x30
                                 for t in api.call('debugger/tracepoints')['log'])
        # Continued genuine playfield activity must prevent further search escalation.
        for _ in range(5):
            api.pulse(4, '12', after=234)
        found = api.state()
        assert sum(t['pc'] == 0x481A and t['bank'] == 0x30
                   for t in api.call('debugger/tracepoints')['log']) == calls_after_return, 'Search continued escalating during playfield activity'
        assert (found['player'], found['ball']) == (1, 1)
        assert found['lock_credits'][0] == locks
        assert not any(t['pc'] == 0x6253 and t['bank'] == 0x2A
                       for t in api.call('debugger/tracepoints')['log'])
        # Recovery may legitimately have released other players' physical locks;
        # return every free ball before expecting an end-of-ball transition.
        for _ in range(8):
            if (api.state()['player'], api.state()['ball']) != (1, 1):
                break
            api.pulse(5, '2000', after=300)
        next_ball = api.wait('next ordinary ball after recovery',
                             lambda s: (s['player'], s['ball']) == (1, 2)
                             and s['switches'][78] == 1 and s['live'] == 1, limit=2400)
        assert next_ball['lock_credits'][0] == locks
        assert next_ball['gears'][0] == found['gears'][0]
        launch_and_validate(api)
        qualify_locks(api)
        for count in range(locks + 1, 4):
            collect_lock(api, count)
            if count < 3:
                launch_and_validate(api)
        multiball = api.wait('legitimate third lock starts MB', lambda s: s['live'] == 3, limit=2400)
        traces = api.call('debugger/tracepoints')['log']
        assert len(traces) < 512
        assert sum(t['pc'] == 0x6253 and t['bank'] == 0x2A for t in traces) == 1
        events = api.call('monitor/log')
        (folder / 'events.json').write_text(json.dumps(events, indent=2) + '\n')
        (folder / 'traces.json').write_text(json.dumps({'log': traces}, indent=2) + '\n')
        result.update(result='PASS', kind='unswitched-area ball search and recovery',
                      physical_locks_before=locks, requested_search_stage=search_stage,
                      frames_until_search=search_frame - start_frame,
                      initial=initial, missing=missing, found=found, next_ball=next_ball,
                      final=multiball, frames=api.frames_run,
                      limitations=['Withheld playfield switch activity models a trapped ball in an unswitched area',
                                   'Simulator auto-routing does not assert the identity of the originally missing ball after lock releases',
                                   'No stuck-switch or failed-device injection; those need a separate fault layer',
                                   'Monitor host timestamps are not used to certify coil pulse duration'])
    return result
from lab.config import REPO as ROOT

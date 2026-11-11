"""Port of authored historical controller readiness_multiplayer. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import json

import pathlib

from readiness_games import ROOT

from readiness_session import session, configure, qualify_locks, collect_lock

def lights(api):
    data = api.memory(0x2E0, 96)
    return [(data[(MAPPING[n] - 1) // 8] >> ((MAPPING[n] - 1) % 8)) & 1
            for n in range(0x16, 0x1F)]

def ensure_playable(api):
    """A replacement can arrive through the inlane when physical locks are shared."""
    for _ in range(12):
        state = api.state()
        if state['switches'][78]:
            api.pulse(1, '8000', on=12, after=240)
        else:
            api.frames(120)
        api.pulse(4, '12', after=180)
        state = api.state()
        if state['live'] == 1 and state['validated'] == 1 and state['phase'] == [0, 0, 0]:
            return state
    raise TimeoutError('No validated playable replacement ball')

def wait_saver(api):
    return api.wait('ball saver expires', lambda s: not ({0xE2, 0xE3, 0xF2} & set(s['task_ids'])),
                    limit=3600, step=60, tasks=True, activity=True)

def drain_turn(api, player, ball):
    wait_saver(api)
    for _ in range(9):
        state = api.state()
        if (state['player'], state['ball']) != (player, ball):
            return state
        api.pulse(5, '2000', after=300)
    return api.wait('all free balls drained and turn advances',
                    lambda s: (s['player'], s['ball']) != (player, ball), limit=2400)

def run_case(folder, port, players, locks, extended):
    with session(folder, port, __file__) as (api, result):
        api.frames(1200)
        configure(api, {0x1B1F: 5 if extended else 3, 0x1B23: 0,
                        0x1B39: 3, 0x1B43: 0, 0x1B51: 1, 0x1B5F: 0,
                        0x1B61: 0, 0x1B9D: 1, 0x1BBF: 0, 0x1BC9: 0,
                        0x1BCB: 99 if extended else 20, 0x1BD5: 99 if extended else 20})
        api.call('debugger/tracepoints', cmd='clear')
        for addr in ['6253', '6A88', '56CB', '5776']:
            api.call('debugger/tracepoints', cmd='add', addr=addr, bank='2A')
        api.button('200', after=300)
        for _ in range(players - 1):
            api.button('200', after=120)
        assert api.memory(0x17A5, 1) == bytes([players])
        ensure_playable(api)
        qualify_locks(api)
        for credit in range(1, locks + 1):
            collect_lock(api, credit, player=1)
            ensure_playable(api)
        before = wait_saver(api)
        saved = {'credits': before['lock_credits'][0], 'gear': before['gears'][0],
                 'qualified': before['qualified'], 'lights': lights(api),
                 'physical_locked': sum(before['switches'][n] for n in [74, 75, 76])}
        assert saved['credits'] == saved['physical_locked'] == locks
        drain_turn(api, 1, 1)
        api.wait('P2 first turn', lambda s: (s['player'], s['ball']) == (2, 1))
        ensure_playable(api)
        qualify_locks(api)
        for credit in range(1, 4):
            collect_lock(api, credit, player=2)
            if credit < 3:
                ensure_playable(api)
        p2_mb = api.wait('P2 legitimate multiball', lambda s: s['live'] == 3, limit=2400)
        assert p2_mb['lock_credits'][0] == locks
        drain_turn(api, 2, 1)
        for player in range(3, players + 1):
            api.wait('later player turn', lambda s: (s['player'], s['ball']) == (player, 1))
            ensure_playable(api)
            drain_turn(api, player, 1)
        returned = api.wait('P1 returns with a served ball',
                            lambda s: (s['player'], s['ball']) == (1, 2)
                            and s['switches'][78] == 1 and s['live'] == 1, limit=2400)
        assert returned['lock_credits'][0] == saved['credits'], 'Other player MB changed owner lock credit'
        assert returned['gears'][0] == saved['gear'], 'Other player MB changed owner gear'
        assert returned['qualified'] == saved['qualified'], 'Other player MB changed owner qualification'
        assert lights(api) == saved['lights'], 'Other player MB changed owner traffic progress'
        assert not any(returned['switches'][n] for n in [74, 75, 76]), 'P2 MB should have released physical locks'
        ensure_playable(api)
        for credit in range(locks + 1, 4):
            collect_lock(api, credit, player=1)
            if credit < 3:
                ensure_playable(api)
        final = api.wait('P1 virtual locks complete legitimate multiball', lambda s: s['live'] == 3, limit=2400)
        traces = api.call('debugger/tracepoints')['log']
        assert len(traces) < 512
        starts = [t for t in traces if t['pc'] == 0x6253 and t['bank'] == 0x2A]
        assert [bytes.fromhex(t['ram'])[0x40F] for t in starts] == [2, 1]
        assert not any(t['pc'] == 0x6A88 and t['bank'] == 0x2A for t in traces)
        (folder / 'traces.json').write_text(json.dumps({'log': traces}, indent=2) + '\n')
        result.update(result='PASS', kind='shared locks: P1 -> P2 regular MB -> P1 return and MB',
                      players=players, owner_locks=locks, extended_profile=extended,
                      saved_owner=saved, p2_multiball=p2_mb, owner_returned=returned,
                      final=final, native_mb_start_players=[2, 1], frames=api.frames_run,
                      limitations=['Regular multiball, P1 owner and P2 recipient, ordinary drain endings only',
                                   'Burn Rubber/Redline, other owner/recipient orders, tilt/restart endings remain separate cases',
                                   'Timer values configured/read back; duration contracts are separate'])
    return result
from lab.config import REPO as ROOT


from lab.runtime import owner_view
MAPPING=owner_view('l5',0x7E5FB,0x7E63C)

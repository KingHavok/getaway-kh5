"""Port of authored historical controller readiness_shared_matrix. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import concurrent.futures

import itertools

import json

import pathlib

from readiness_session import session, configure, qualify_locks, collect_lock

from readiness_multiplayer import ensure_playable, wait_saver, drain_turn, lights

def advance_to(api, target, players):
    for _ in range(players + 1):
        state = api.state()
        if state['player'] == target and state['phase'] == [0, 0, 0]:
            return state
        assert state['phase'][1] == 0, 'Game ended before the intended owner/recipient turn'
        ensure_playable(api)
        state = api.state()
        drain_turn(api, state['player'], state['ball'])
    raise TimeoutError('Expected player turn not reached')

def run_case(folder, port, spec):
    players, owner, recipient, locks = [spec[k] for k in ['players', 'owner', 'recipient', 'locks']]
    extended = spec['extended']
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
        advance_to(api, owner, players)
        ensure_playable(api)
        qualify_locks(api)
        for credit in range(1, locks + 1):
            collect_lock(api, credit, player=owner)
            ensure_playable(api)
        before = wait_saver(api)
        saved = {'credits': before['lock_credits'][owner - 1], 'gear': before['gears'][owner - 1],
                 'qualified': before['qualified'], 'lights': lights(api),
                 'physical_locked': sum(before['switches'][n] for n in [74, 75, 76])}
        assert saved['credits'] == saved['physical_locked'] == locks
        owner_ball = before['ball']
        drain_turn(api, owner, owner_ball)
        advance_to(api, recipient, players)
        ensure_playable(api)
        qualify_locks(api)
        for credit in range(1, 4):
            collect_lock(api, credit, player=recipient)
            if credit < 3:
                ensure_playable(api)
        recipient_mb = api.wait('recipient legitimate MB', lambda s: s['live'] == 3, limit=2400)
        assert recipient_mb['lock_credits'][owner - 1] == locks
        drain_turn(api, recipient, recipient_mb['ball'])
        advance_to(api, owner, players)
        returned = api.wait('owner served after recipient MB',
                            lambda s: s['player'] == owner and s['ball'] == owner_ball + 1
                            and s['switches'][78] == 1 and s['live'] == 1, limit=2400)
        assert returned['lock_credits'][owner - 1] == saved['credits']
        assert returned['gears'][owner - 1] == saved['gear']
        assert returned['qualified'] == saved['qualified'] and lights(api) == saved['lights']
        assert not any(returned['switches'][n] for n in [74, 75, 76])
        ensure_playable(api)
        for credit in range(locks + 1, 4):
            collect_lock(api, credit, player=owner)
            if credit < 3:
                ensure_playable(api)
        final = api.wait('owner completes virtual-lock MB', lambda s: s['live'] == 3, limit=2400)
        traces = api.call('debugger/tracepoints')['log']
        assert len(traces) < 512
        starts = [t for t in traces if t['pc'] == 0x6253 and t['bank'] == 0x2A]
        assert [bytes.fromhex(t['ram'])[0x40F] for t in starts] == [recipient, owner]
        assert not any(t['pc'] == 0x6A88 and t['bank'] == 0x2A for t in traces)
        (folder / 'traces.json').write_text(json.dumps({'log': traces}, indent=2) + '\n')
        result.update(result='PASS', kind='all directed regular-MB shared-lock pairs',
                      players=players, owner=owner, recipient=recipient, owner_locks=locks,
                      extended_profile=extended, saved_owner=saved, recipient_multiball=recipient_mb,
                      owner_returned=returned, final=final, native_mb_start_players=[recipient, owner],
                      frames=api.frames_run,
                      limitations=['Regular MB and ordinary drains only; Burn Rubber, Redline, tilt and restart are not inferred',
                                   'Extended timing values configured, not mode-duration assertions'])
    return result
from lab.config import REPO as ROOT

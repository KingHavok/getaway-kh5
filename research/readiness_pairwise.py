"""Port of authored historical controller readiness_pairwise. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import json

import pathlib

from readiness_games import ROOT

from readiness_session import session, configure, qualify_locks, collect_lock

from readiness_multiplayer import ensure_playable

CMOS = {'balls_per_game': 0x1B1F, 'getaway_timer': 0x1BCB,
        'supercharger_timer': 0x1BD5, 'tournament': 0x1B51,
        'restart': 0x1B5F, 'replay_award': 0x1B39,
        'multiball_percent': 0x1BD3, 'extra_ball_memory': 0x1BC7,
        'consolation_ball': 0x1BC9, 'timed_plunger': 0x1BC1,
        'flipper_plunger': 0x1BC3, 'kickback_setting': 0x1BC5}

def run_case(folder, port, spec):
    with session(folder, port, __file__) as (api, result):
        api.frames(1200)
        values = {CMOS[k]: v for k, v in spec.items() if k != 'players'}
        values.update({0x1B9D: 1, 0x1B23: 0, 0x1BBF: 0, 0x1B43: 0, 0x1B61: 0})
        configure(api, values)
        api.call('debugger/tracepoints', cmd='clear')
        for addr in ['6253', '6A88', '56CB']:
            api.call('debugger/tracepoints', cmd='add', addr=addr, bank='2A')
        api.button('200', after=300)
        for _ in range(spec['players'] - 1):
            api.button('200', after=120)
        assert api.memory(0x17A5, 1) == bytes([spec['players']])
        ensure_playable(api)
        qualify_locks(api)
        for credit in range(1, 4):
            state = collect_lock(api, credit)
            if credit < 3:
                # The credit precedes the replacement-ball serve. Zero live
                # balls during that interval is expected; three is premature.
                assert state['live'] < 3, 'Multiball started before third lock'
                ensure_playable(api)
        final = api.wait('legitimate three-ball MB', lambda s: s['live'] == 3, limit=2400)
        assert (final['player'], final['ball'], final['phase']) == (1, 1, [0, 0, 0])
        traces = api.call('debugger/tracepoints')['log']
        assert len(traces) < 512
        assert sum(t['pc'] == 0x6253 and t['bank'] == 0x2A for t in traces) == 1
        assert not any(t['pc'] in [0x6A88, 0x56CB] and t['bank'] == 0x2A for t in traces)
        for address, value in values.items():
            assert int.from_bytes(api.memory(address, 2), 'big') == value
        (folder / 'traces.json').write_text(json.dumps({'log': traces}, indent=2) + '\n')
        result.update(result='PASS', selected_settings=spec, final=final, frames=api.frames_run,
                      limitations=['Configuration-pair coexistence through a common regular-MB flow only',
                                   'Does not measure timers, exercise every setting-specific feature, or cover all higher-order combinations',
                                   'Extra-ball awards disabled; memory/consolation feature contracts remain separate'])
    return result
from lab.config import REPO as ROOT

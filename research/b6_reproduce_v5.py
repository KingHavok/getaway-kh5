"""Port of authored historical controller b6_reproduce_v5. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import hashlib

import json

import pathlib

import traceback

import urllib.request

from fault_lab_candidate import session, setup, configure, qualify_locks, collect_lock

from readiness_multiplayer import ensure_playable, drain_turn

import remaining_multiball_matrix_v4 as modes

def rombyte(address):
    return ROM[0x28000 + address - 0x4000]

def threshold(gear):
    offset = 0x28000 + 0x4383 - 0x4000 + gear * 2
    pointer = int.from_bytes(ROM[offset:offset + 2], 'big')
    return rombyte(pointer + 12)

POINTS = [0x42F6, 0x4317, 0x4328, 0x48EE, 0x4473, 0x4478,
          0x4480, 0x45BB, 0x6253, 0x6A88, 0x6AD4, 0x475C]

class Experiment:
    def __init__(self, api, folder, replay=False):
        self.api, self.folder, self.replay = api, folder, replay
        self.ledger, self.snapshots = [], []
        original = api.call

        def call(path, **params):
            mutation = (path.startswith('input') or path == 'debugger/memory/write'
                        or path == 'debugger/control' and params.get('cmd') == 'frames'
                        or path == 'debugger/tracepoints' and params.get('cmd') in ['clear', 'add'])
            if mutation and not replay:
                self.ledger.append(dict(path=path, params=params))
            return original(path, **params)
        api.call = call

    def snapshot(self, label):
        if not self.replay:
            self.ledger.append(dict(checkpoint=label))
        marker = self.api.marker(label)
        player = marker['state']['player']
        raw = self.api.memory(0x900, 0x100)
        gear = marker['state']['gears'][player - 1]
        rpm = raw[0x2B + (player - 1) * 54]
        item = dict(label=label, frame=self.api.frames_run, marker=marker,
                    player_rpm=[raw[0x2B + p * 54] for p in range(4)],
                    current_rpm=rpm, current_gear=gear,
                    threshold=threshold(gear) if 0 <= gear <= 5 else None,
                    rpm_target=self.api.memory(0x809, 1)[0],
                    game_globals=self.api.memory(0x800, 0xE8).hex(),
                    inhibit_bitmap=self.api.memory(0x320, 0x40).hex(),
                    player_records=raw.hex())
        traces = self.api.call('debugger/tracepoints')
        assert len(traces['log']) < 512, 'Trace window overflow: preserve as fixture failure'
        (self.folder / ('trace-%03d.json' % len(self.snapshots))).write_text(json.dumps(traces, indent=2) + '\n')
        self.snapshots.append(item)
        (self.folder / 'observations.json').write_text(json.dumps(self.snapshots, indent=2) + '\n')
        if label.startswith('probe-'):
            with urllib.request.urlopen(f'http://127.0.0.1:{self.api.port}/api/dmd/pnm', timeout=15) as response:
                pixels = response.read()
            assert pixels.startswith(b'P'), 'DMD endpoint did not return a PNM image'
            image_path = self.folder / ('dmd-%03d.pgm' % (len(self.snapshots) - 1))
            image_path.write_bytes(pixels)
            self.api.log.write(json.dumps(dict(frame_budget_total=self.api.frames_run,
                path='dmd/pnm', params={}, response=dict(file=image_path.name,
                sha256=hashlib.sha256(pixels).hexdigest()))) + '\n')
            self.api.log.flush()
        if not self.replay:
            self.api.call('debugger/tracepoints', cmd='clear')
            for address in POINTS:
                self.api.call('debugger/tracepoints', cmd='add', addr=f'{address:04X}', bank='2A')
        print(self.folder.name, label, 'gear', gear, 'rpm', rpm,
              'target', item['rpm_target'], 'live', marker['state']['live'], flush=True)
        return item

def jet_second(api):
    api.call('input', sw=31, val=1)
    api.frames(6)
    api.call('input', sw=31, val=0)
    api.frames(54)

def wait_no_saver(api):
    for _ in range(90):
        if not ({0xE2, 0xE3, 0xF2} & set(api.state(tasks=True)['task_ids'])):
            return
        jet_second(api)
    raise TimeoutError('Initial/multiball saver did not expire')

def wait_grace(api):
    for _ in range(150):
        if not ({0x89, 0xF7} & set(api.state(tasks=True)['task_ids'])):
            return
        jet_second(api)
    raise TimeoutError('Getaway grace did not clean up')

def to_third_short(api, experiment):
    for index in range(20):
        state = api.state()
        if state['gears'][state['player'] - 1] == 3:
            break
        assert state['gears'][state['player'] - 1] < 3, 'Preparation skipped third gear'
        api.pulse(4, '12', after=180)
        api.pulse(4, '400', on=12, after=180)
        experiment.snapshot('prepare-gear-%02d' % index)
    else:
        raise TimeoutError('Could not reach third gear through shots and shifter')
    for index in range(12):
        state = api.state()
        assert state['gears'][state['player'] - 1] == 3
        rpm = api.memory(0x92B + (state['player'] - 1) * 54, 1)[0]
        gap = threshold(3) - rpm
        if 0 < gap <= rombyte(0x42F0 + 3):
            return experiment.snapshot('one-loop-short')
        assert gap > 0, ('Already completed third gear during preparation', rpm)
        api.pulse(4, '12', after=180)
        experiment.snapshot('prepare-third-%02d' % index)
    raise TimeoutError('Third RPM preparation made no progress')

def lock_two(api, experiment):
    qualify_locks(api)
    for credit in [1, 2]:
        collect_lock(api, credit)
        ensure_playable(api)
    experiment.snapshot('two-locks')

def all_balls_free(api):
    return api.wait('all live simulator balls free before shot/drain',
        lambda state: sum(b['installed'] and b['state'] == 258 for b in api.io()['balls']) == state['live'],
        limit=4800, step=60)

def finish_mb(api, experiment):
    wait_no_saver(api)
    for desired in [2, 1]:
        all_balls_free(api)
        wait_no_saver(api)
        api.pulse(5, '2000', after=300)
        api.wait('one multiball drain', lambda s: s['live'] == desired, limit=2400)
    experiment.snapshot('multiball-ended')

def hideout_returns(api, experiment):
    for award in range(3):
        all_balls_free(api)
        for shot in range(18):
            if api.state()['switches'][54] == 1:
                break
            all_balls_free(api)
            api.pulse(4, '5', after=300)
            experiment.snapshot('relight-%d-sc-%d' % (award, shot))
        api.wait('Hideout ramp lowered', lambda s:s['switches'][54] == 1, limit=2400)
        all_balls_free(api)
        api.pulse(4, '6', after=480)
        experiment.snapshot('hideout-return-%d' % (award + 1))
    all_balls_free(api)
    for _ in range(30):jet_second(api)
    wait_no_saver(api)

def prepare(api, experiment, history):
    setup(api, players=2 if history.startswith("multiplayer_") else 1, extended=False)
    ensure_playable(api)
    experiment.snapshot('launched')
    if history.startswith('mb_'):
        lock_two(api, experiment)
        to_third_short(api, experiment)
        collect_lock(api, 3)
        api.wait('three-ball multiball', lambda s: s['live'] == 3, limit=2400)
        experiment.snapshot('third-short-multiball-start')
        wait_no_saver(api)
        # Qualify the jackpot through real Supercharger shots, as required for
        # native Getaway Time. Do not infer that qualification from a timer.
        for index in range(12):
            if api.state()['switches'][54] == 1:
                break
            api.pulse(4, '5', after=300)
            experiment.snapshot('supercharger-%02d' % index)
        if history == 'mb_restart':
            hideout_returns(api, experiment)
        finish_mb(api, experiment)
        if history == 'mb_expired':
            wait_grace(api)
            experiment.snapshot('grace-cleaned-up')
    elif history in ['redline_after', 'redline_then_regular', 'regular_then_redline', 'redline_restart_after']:
        lock_two(api, experiment)
        if history == 'regular_then_redline':
            collect_lock(api, 3)
            api.wait('ordinary multiball', lambda s: s['live'] == 3, limit=2400)
            finish_mb(api, experiment)
            wait_grace(api)
            experiment.snapshot('ordinary-multiball-grace-cleaned-up')
        modes.redline(api, 1, False)
        experiment.snapshot('redline-started')
        if history == 'redline_restart_after':
            hideout_returns(api, experiment)
        finish_mb(api, experiment)
        if history == 'redline_then_regular':
            collect_lock(api, 3)
            api.wait('third-lock ordinary multiball after Redline', lambda s: s['live'] == 3, limit=2400)
            experiment.snapshot('ordinary-multiball-during-redline-grace')
            finish_mb(api, experiment)
        wait_grace(api)
        experiment.snapshot('redline-grace-cleaned-up')
        to_third_short(api, experiment)
    elif history.startswith('multiplayer_'):
        to_third_short(api, experiment)
        experiment.snapshot('owner-third-short-before-player-change')
        drain_turn(api, 1, 1)
        ensure_playable(api)
        assert api.state()['player'] == 2
        qualify_locks(api)
        for credit in [1, 2]:
            collect_lock(api, credit, player=2)
            ensure_playable(api)
        if history == 'multiplayer_redline':
            modes.redline(api, 2, False)
        else:
            collect_lock(api, 3, player=2)
            api.wait('other player ordinary multiball', lambda s: s['live'] == 3, limit=2400)
        experiment.snapshot('other-player-multiball')
        drain_turn(api, 2, 1)
        api.wait('P1 next ball served', lambda s: s['player'] == 1 and s['ball'] == 2 and s['switches'][78], limit=2400)
        experiment.snapshot('owner-third-short-next-ball-before-launch')
        api.pulse(1, '8000', on=12, after=240)
        api.wait('P1 next ball live', lambda s:s['player']==1 and s['ball']==2 and s['live']==1 and s['phase']==[0,0,0])
        experiment.snapshot('owner-returned-after-other-player-mode')
    elif history == 'baseline':
        to_third_short(api, experiment)
    else:
        raise ValueError(history)

def probe(api, experiment):
    before = experiment.snapshot('probe-before-final-loop')
    assert before['current_gear'] == 3
    assert 0 <= before['threshold'] - before['current_rpm'] <= rombyte(0x42F3), 'Not one loop short or already RPM-complete'
    if before['current_rpm'] < before['threshold']:
        api.pulse(4, '12', after=180)
    after = experiment.snapshot('probe-after-final-loop')
    api.pulse(4, '400', on=12, after=180)
    shifted = experiment.snapshot('probe-after-shift')
    if shifted['current_gear'] > 3:
        return 'ADVANCED_ON_FIRST_LOOP_AND_SHIFT'
    # An active mode is not automatically a bug. Allow its real cleanup, then
    # repeat valid loops/shifts before flagging a persistent third-gear stall.
    wait_grace(api)
    api.frames(180)
    experiment.snapshot('probe-after-grace-cleanup-without-another-loop')
    api.pulse(4, '400', on=12, after=180)
    shifted = experiment.snapshot('probe-shift-alone-after-grace')
    if shifted['current_gear'] > 3:
        return 'ADVANCED_AFTER_GRACE_WITHOUT_ANOTHER_LOOP'
    for index in range(6):
        api.pulse(4, '12' if index % 2 == 0 else '11', after=300)
        api.pulse(4, '400', on=12, after=180)
        last = experiment.snapshot('retry-%02d' % index)
        if last['current_gear'] > 3:
            return 'ADVANCED_AFTER_WAIT_OR_RETRY'
    return 'PERSISTENT_THIRD_GEAR_STALL_CANDIDATE_REQUIRES_TRACE_REVIEW'

def run_official(folder, port, history, delay=0):
    with session(folder, port, __file__, game='gw_l5') as (api, record):
        experiment = Experiment(api, folder)
        try:
            prepare(api, experiment, history)
            seconds, remainder = divmod(delay, 60)
            for _ in range(seconds):jet_second(api)
            if remainder:api.frames(remainder)
            if delay:experiment.snapshot('delay-before-probe-%d' % delay)
            outcome = probe(api, experiment)
            record.update(result='PASS', experiment_completed=True, history=history,
                          probe_outcome=outcome, probe_delay_frames=delay, checkpoints=len(experiment.snapshots),
                          meaning='Experiment completion, not proof B6 is absent')
        finally:
            (folder / 'stimulus.json').write_text(json.dumps(experiment.ledger, indent=2) + '\n')
    return record

def replay(folder, port, original):
    ledger_path = original / 'stimulus.json'
    ledger = json.loads(ledger_path.read_text())
    with session(folder, port, __file__, game='gw_g6') as (api, record):
        experiment = Experiment(api, folder, replay=True)
        for item in ledger:
            if 'checkpoint' in item:
                experiment.snapshot(item['checkpoint'])
            else:
                params = item['params']
                api.call(item['path'], **params)
                if item['path'] == 'debugger/control' and params.get('cmd') == 'frames':
                    # replaying call() alone must wait for completion without
                    # issuing a second frame request or changing its budget.
                    import time
                    deadline = time.monotonic() + 60
                    while True:
                        info = api.call('info')
                        if info['paused']:
                            assert info['frames_remaining'] == 0
                            break
                        assert time.monotonic() < deadline
                        time.sleep(.01)
                    api.frames_run += params['count']
        record.update(result='PASS', experiment_completed=True,
                      replay_of=str(original.resolve()),
                      stimulus_sha256=hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
                      checkpoints=len(experiment.snapshots),
                      meaning='Exact external inputs/frame requests replayed; compare observations for B6')
    return record
from lab.config import REPO as ROOT
from lab.runtime import owner_view
ROM=owner_view('l5')

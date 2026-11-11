"""Port of authored historical controller readiness_games. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import concurrent.futures

import hashlib

import json

import os

import pathlib

import signal

import subprocess

import sys

import time

import urllib.parse

import urllib.request

def full_game(api, balls, players, extended):
    api.frames(1200)
    # Disable automatic extra balls/name entry so this case has a precise
    # ordinary-ball denominator. Those features require separate contracts.
    values = {
        0x1B1F: balls, 0x1B23: 0, 0x1B39: 3, 0x1B43: 0,
        0x1B51: 0, 0x1B5F: 0, 0x1B61: 0, 0x1B9D: 1,
        0x1BBF: 0, 0x1BC9: 0, 0x1BCB: 99 if extended else 20,
        0x1BD5: 99 if extended else 20,
    }
    api.call('debugger/memory/write', addr='3FFD', data='B4')
    for addr, value in values.items():
        api.call('debugger/memory/write', addr=f'{addr:04X}', data=f'{value:04X}')
    api.call('debugger/memory/write', addr='3FFD', data='00')
    for addr, value in values.items():
        assert int.from_bytes(api.memory(addr, 2), 'big') == value
    api.call('monitor', cmd='clear')
    api.call('monitor', cmd='add', type='sol', id=7)
    api.button('200', after=300)
    for _ in range(players - 1):
        api.button('200', after=120)
    assert api.memory(0x17A5, 1) == bytes([players])
    turns = []
    for ball in range(1, balls + 1):
        for player in range(1, players + 1):
            state = api.wait('expected shooter/turn',
                             lambda s: (s['player'], s['ball']) == (player, ball)
                             and s['switches'][78] == 1 and s['live'] == 1)
            assert state['phase'] == [0, 0, 0]
            assert not any(state['switches'][n] for n in [74, 75, 76])
            api.pulse(1, '8000', on=12, after=240)
            api.pulse(4, '12', after=180)
            state = api.wait('validated playfield', lambda s: s['validated'] == 1, limit=600)
            state = api.wait('native ball saver expired',
                             lambda s: not ({0xE2, 0xE3, 0xF2} & set(s['task_ids'])),
                             limit=2400, step=60, tasks=True, activity=True)
            assert (state['player'], state['ball'], state['live']) == (player, ball, 1)
            turns.append({'player': player, 'ball': ball, 'frame': api.frames_run,
                          'gear': state['gears'][player - 1], 'saver_tasks_absent': True})
            api.pulse(5, '2000')
            state = api.wait('drain advances turn or ends game',
                             lambda s: s['phase'][1] == 1 or (s['player'], s['ball']) != (player, ball),
                             limit=2400)
            if ball == balls and player == players:
                state = api.wait('final attract', lambda s: s['phase'][1] == 1, limit=1800)
            else:
                assert state['phase'][1] == 0, ('Early game over', ball, player)
    assert len(turns) == balls * players
    assert state['phase'][1] == 1
    assert all(state['switches'][n] == 1 for n in [56, 57, 58])
    assert not any(state['switches'][n] for n in [74, 75, 76, 78])
    events = api.call('monitor/log')['actions']
    assert not any(e['type'] == 'sol' and e['id'] == 7 and e['val'] for e in events), 'Unexpected knocker activation'
    for addr, value in values.items():
        assert int.from_bytes(api.memory(addr, 2), 'big') == value
    return {'result': 'PASS', 'kind': 'full ordinary-ball game order', 'balls_per_game': balls,
            'players': players, 'extended_timer_values': extended,
            'ordinary_turns': turns, 'frames': api.frames_run,
            'knocker_activations': 0, 'settings': {f'{a:04X}': v for a, v in values.items()},
            'limits': ['Extra balls and consolation are deliberately disabled for exact ordinary-ball counting',
                       'Extended timing values are read back; this case does not measure those mode durations',
                       'Replay suppression is observed; a replay-triggering positive control is still required',
                       'Direct CMOS setup does not verify menu operation or power-cycle persistence']}
from lab.api import API
from lab.config import REPO as ROOT,sha
HARNESS_SHA256=sha(__file__)

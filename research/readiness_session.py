"""Port of authored historical controller readiness_session. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import contextlib

import hashlib

import json

import os

import pathlib

import signal

import subprocess

import sys

import time

import urllib.request

from readiness_games import API, ROOT

def configure(api, values):
    api.call('debugger/memory/write', addr='3FFD', data='B4')
    for addr, value in values.items():
        assert 0x1B1D <= addr < 0x1BDF and (addr - 0x1B1D) % 2 == 0
        api.call('debugger/memory/write', addr=f'{addr:04X}', data=f'{value:04X}')
    api.call('debugger/memory/write', addr='3FFD', data='00')
    for addr, value in values.items():
        assert int.from_bytes(api.memory(addr, 2), 'big') == value

def launch_and_validate(api):
    api.wait('served ball', lambda s: s['switches'][78] == 1 and s['live'] == 1)
    api.pulse(1, '8000', on=12, after=240)
    api.pulse(4, '12', after=180)
    return api.wait('playfield validated', lambda s: s['validated'] == 1 and s['live'] == 1)

def qualify_locks(api):
    for _ in range(3):
        if api.state()['qualified'] == 3:
            return
        for switch in [51, 52, 53, 41, 42, 43, 36, 37, 38]:
            api.call('input', sw=switch, val=1)
            api.frames(6)
            api.call('input', sw=switch, val=0)
            api.frames(24)
    assert api.state()['qualified'] == 3, 'Could not qualify all locks through targets'

def collect_lock(api, expected, player=1):
    api.wait('lock ramp down', lambda s: s['switches'][54] == 1)
    api.pulse(4, '6')
    # Native MB initialization consumes the third credit; observe the durable
    # three-ball state too rather than requiring that transient credit to linger.
    return api.wait('lock credit', lambda s: s['lock_credits'][player - 1] == expected
                    or (expected == 3 and s['live'] == 3))
from lab.runtime import session

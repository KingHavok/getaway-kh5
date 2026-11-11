"""Port of authored historical controller pilot_burn_rubber. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import json

import pathlib

from fault_lab import session,setup,ensure_playable,qualify_locks,collect_lock

def tunnel(api):
    api.wait('free ball before tunnel',lambda s:s['live']==1 and s['phase']==[0,0,0],limit=1800)
    api.pulse(4,'800',after=30)
    for _ in range(120):
        io=api.io();state=api.state()
        if state['live']>1:return state
        if not state['switches'][77] and any(b['installed'] and b['state']==258 for b in io['balls']):return state
        api.frames(30)
    raise TimeoutError('Tunnel did not release its ball')
from lab.config import REPO as ROOT

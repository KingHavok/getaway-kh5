"""Port of authored historical controller pilot_donut_trap. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import json

import pathlib

from fault_lab import session,setup,ensure_playable,qualify_locks,wait_saver

def edge(api,number,on=6):
    api.call('input',sw=number,val=1);api.frames(on)
    api.call('input',sw=number,val=0)
from lab.config import REPO as ROOT

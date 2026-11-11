"""Port of authored historical controller release_g6_lab_v2. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import hashlib

import json

import pathlib

import re

import struct

import urllib.request

import zlib

from fault_lab_candidate_sound import session, configure

from readiness_games import ROOT

G6_SHA1 = '138156d02c1e615303d0c747e84b34e1b970cf83'

def adapt(api):
    original = api.frames
    def frames(count):
        while count:
            chunk = min(count, 600)
            original(chunk)
            count -= chunk
    api.frames = frames
    return api

def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)

def dmd(api, folder, label):
    with urllib.request.urlopen(f'http://127.0.0.1:{api.port}/api/dmd/pnm', timeout=15) as response:
        raw = response.read()
    match = re.match(br'P5\n(\d+) (\d+)\n255\n', raw)
    assert match
    width, height = map(int, match.groups())
    pixels = raw[match.end():]
    assert len(pixels) == width * height
    path = folder / (label + '.pgm')
    path.write_bytes(raw)
    # A nearest-neighbour enlargement for reading the unaltered DMD pixels.
    rows = []
    for y in range(height):
        row = b''.join(bytes([value]) * 6 for value in pixels[y * width:(y + 1) * width])
        rows.extend([b'\0' + row] * 6)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width * 6, height * 6, 8, 0, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b'')
    image = folder / (label + '.png')
    image.write_bytes(png)
    api.log.write(json.dumps(dict(frame_budget_total=api.frames_run, path='dmd/pnm', params={},
        response=dict(file=path.name, sha256=hashlib.sha256(raw).hexdigest(), review=image.name))) + '\n')
    api.log.flush()
    return str(image)

def profile(api, players=1, kids=False, tournament=False, awards=True):
    api.frames(1200)
    configure(api, {0x1B1F:5 if kids else 3, 0x1B21:1, 0x1B23:4 if awards else 0,
        0x1B39:3, 0x1B43:0, 0x1B51:int(tournament), 0x1B5F:0,
        0x1B61:0, 0x1B9D:1, 0x1BBF:35 if awards else 0,
        0x1BC9:0, 0x1BCB:99 if kids else 20, 0x1BD3:20,
        0x1BD5:99 if kids else 20})
    api.button('200', after=300)
    for _ in range(players - 1):
        api.button('200', after=120)
    assert api.memory(0x17A5, 1)[0] == players

def trace(api, addresses):
    api.call('debugger/tracepoints', cmd='clear')
    for address, bank in addresses:
        api.call('debugger/tracepoints', cmd='add', addr=f'{address:04X}', bank=f'{bank:02X}')

def save_trace(api, folder, label):
    data = api.call('debugger/tracepoints')
    assert len(data['log']) < 512, 'Trace window full'
    (folder / (label + '.traces.json')).write_text(json.dumps(data, indent=2) + '\n')
    return data['log']
from lab.config import REPO as ROOT
from lab.runtime import LAB as BASE

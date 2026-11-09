#!/usr/bin/env python3
"""Verify a local KH5 output/read-back without requiring or publishing its input."""
import argparse,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from kh5patch.core import identity
p=argparse.ArgumentParser(description=__doc__);p.add_argument('image',type=pathlib.Path);a=p.parse_args()
expected=json.loads((ROOT/'patches/release.json').read_text())['target'];data=a.image.read_bytes()
if identity(data)!=expected or int.from_bytes(data[-18:-16],'big')!=int(expected['wpc_checksum'],16):p.exit(1,'FAIL: not the exact KH5 release image\n')
print('PASS: exact KH5 image, native checksum '+expected['wpc_checksum'])

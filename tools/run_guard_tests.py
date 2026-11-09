#!/usr/bin/env python3
"""Generate a PRIVATE NEVER-BURN fixture and run 48 native CPU guard cases."""
import argparse,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from kh5patch.core import identity
from replay import emulator

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--emulator',type=pathlib.Path,required=True);p.add_argument('--rom',type=pathlib.Path,required=True);p.add_argument('--sound',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--port',type=int,default=9051);a=p.parse_args()
 data=bytearray(a.rom.read_bytes());meta=json.loads((ROOT/'patches/release.json').read_text())
 if identity(data)!=meta['target']:p.error('Use the exact generated KH5 image as source')
 if hashlib.sha1(a.sound.read_bytes()).hexdigest()!='e6b7ccef250db0c801e3dd8ebf93522b466ca1ec':p.error('Matching user-owned U18 required')
 bootstrap=bytes.fromhex('862AB73FFCCC12347E6091');start=0x7fb40
 if data[start:start+len(bootstrap)]!=b'\xff'*len(bootstrap):p.error('Fixture hole is not free')
 data[start:start+len(bootstrap)]=bootstrap;output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
 fixture=output/'UNIT_ONLY_NEVER_BURN.bin';fixture.write_bytes(data);rompath=output/'PRIVATE-roms';game=rompath/'gw_kh5';game.mkdir(parents=True)
 (game/'getaw_kh5.rom').write_bytes(data);(game/'u18snd').write_bytes(a.sound.read_bytes())
 # The registered game hash deliberately differs from a unit fixture. No game
 # checksum is bypassed in the real image; the fixture starts at our bootstrap.
 with emulator(a.emulator.resolve(),output/'native-unit',rompath,a.port):
  subprocess.run([sys.executable,str(ROOT/'tools/check_guard.py'),str(fixture),'--expect','guarded','--task-states','--port',str(a.port),'--log',str(output/'unit-summary.json')],check=True)
 print('48 native unit cases passed. Fixture is NOT a playable/burn image.')
if __name__=='__main__':main()

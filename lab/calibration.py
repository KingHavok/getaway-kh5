"""Independent authored CPU waveform and forced-sensor calibration. NEVER BURN.
Port of the project's original build_fault_pinmame/test_fault_instrumentation.
This generated NOP-filled image contains no game program; U18 stays owner-local.
"""
import hashlib,json
from pathlib import Path
from . import runtime
from .config import verify_image,sound,sha
from .api import API
from replay import emulator

def run(folder,port):
 # Mask interrupts, emit independent 200-iteration DECB/BNE delay pulses,
 # then repeatedly sample ordinary/inverted-matrix/flipper inputs into RAM.
 program=bytes.fromhex('1A50 10CE0FF0 8601 B73FE1 C6C8 5A26FD 4F B73FE1 '
  '86FF B73FD4 86FE B73FD4 C6C8 5A26FD 86FF B73FD4 '
  '8640 B73FEA B63FE9 B70200 8680 B73FEA B63FE9 B70201 B63FD4 B70202 20E2')
 image=bytearray(b'\x12'*524288);image[0x78000:0x78000+len(program)]=program;image[-2:]=b'\x80\0'
 folder.mkdir(parents=True,exist_ok=False);roms=folder/'PRIVATE-roms';game=roms/'gw_kh5';game.mkdir(parents=True)
 (game/'getaw_kh5.rom').write_bytes(image);(game/'u18snd').write_bytes(sound(runtime.PROJECT))
 checks=[];raw=folder/'raw-coils.jsonl'
 with (folder/'actions.jsonl').open('w') as log:
  with emulator(Path(runtime.PROJECT['emulator']),folder/'runtime',roms,port,io_trace=raw) as transport:
   api=API(port,log,unit=True);api.frames(2);initial=api.io()
   if len(runtime.installed(initial))!=3:raise AssertionError('Installed-ball calibration differs')
   def sensor(io,n):return next(s for s in io['switches'] if s['id']==n)
   for number,address,mask,inverted in [(74,0x200,8,False),(81,0x201,1,True),(111,0x202,1,True)]:
    physical=sensor(initial,number)['physical']
    for forced in [1,0,-1]:
     api.fault('switch',number,forced);api.frames(2);s=sensor(api.io(),number);expected=physical if forced<0 else forced
     if s['physical']!=physical or s['last_seen']!=expected or s['effective']!=expected or not s['reads']:raise AssertionError('Forced sensor accounting differs')
     if (bool(api.memory(address,1)[0]&mask)^inverted)!=bool(expected):raise AssertionError('Real CPU sensor read differs')
     checks.append(dict(sensor=number,forced=forced,physical=physical,cpu_read=expected))
   io=api.io();rows=[json.loads(line) for line in raw.read_text().splitlines()];writes=[r for r in rows if r['kind']=='write']
   ordinary=[r for r in writes if r['address']==0x3FE1];flip=[r for r in writes if r['address']==0x3FD4]
   if [r['value'] for r in ordinary]!=[1,0] or [r['value'] for r in flip]!=[255,254,255]:raise AssertionError('Known waveform output sequence differs')
   expected=1009/2000000;measured=[ordinary[1]['time']-ordinary[0]['time'],flip[2]['time']-flip[1]['time']]
   if any(abs(v-expected)>=.000003 for v in measured):raise AssertionError('Known-cycle waveform clock calibration differs')
   if [r['seq'] for r in writes]!=list(range(1,len(writes)+1)):raise AssertionError('Raw output write sequence lost events')
 entry,_=verify_image(runtime.PROJECT,runtime.selected())
 record=dict(result='PASS',image_name=runtime.selected(),image_sha1=entry['identity']['sha1'],image_sha256=entry['identity']['sha256'],
  fixture_sha256=hashlib.sha256(image).hexdigest(),emulator_sha256=sha(runtime.PROJECT['emulator']),source_sha256=sha(__file__),
  unit=True,selected_game_firmware_executed=False,catalogue_mismatch_expected=True,fixture_kind='UNIT_ONLY_NEVER_BURN independent CPU calibration',
  source_nvram_unchanged=True,frames=api.frames_run,final_io=io,sensor_checks=checks,
  expected_pulse_seconds=expected,observed_pulse_seconds=measured,qualification='Instrumentation only; not a game-ROM or physical thermal qualification')
 (folder/'result.json').write_text(json.dumps(record,indent=2)+'\n');return record

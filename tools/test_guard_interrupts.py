#!/usr/bin/env python3
"""Owner-local native interrupt tests; all generated fixtures MUST NEVER be burned.

The core performs actual IRQ/FIRQ stacking and runs the unmodified native handlers.
IRQ and DMD-FIRQ are asserted through debugger CPU pending-line registers; a timer
FIRQ is raised by the emulated WPC timer itself. No handler is replaced by a stub.
Only own bootstrap/parking instructions and checksum words are added to fixtures.
An optional exact L5C reference supplies its numeric guard locally, never publicly.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from kh5patch.core import checksum,identity
from replay import emulator
from compare_guards import REFERENCE_SHA1

SCENARIOS=[('unqualified',0,1,0,0x1234,0),('zero_live',1,0,0,0x80FF,0x8003),
 ('two_live',1,2,0,0xFFFF,0),('overflow',1,0x80,0,0xA55A,0x8000),
 ('qualified_high_bit',0x80,1,0,0x7F00,0),('qualified_max',255,1,0,0x00FF,1),
 ('pending_F2',1,1,0xF2,0xFF00,0),('running_F3',1,1,0xF3,0x1234,0)]
MODES=['IRQ','DMD_FIRQ','TIMER_FIRQ','IRQ_WITH_NESTED_DMD_FIRQ']


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for option in ['emulator','rom','sound','output']:parser.add_argument('--'+option,type=Path,required=True)
 parser.add_argument('--reference',type=Path);parser.add_argument('--port',type=int,default=9055)
 a=parser.parse_args();release=json.loads((ROOT/'patches/release.json').read_text())
 source=a.rom.read_bytes();sound=a.sound.read_bytes()
 if identity(source)!=release['target']:parser.error('Exact qualified KH5 required')
 if hashlib.sha1(sound).hexdigest()!='e6b7ccef250db0c801e3dd8ebf93522b466ca1ec':parser.error('Matching owner-supplied U18 required')
 variants=[('KH5',source)]
 if a.reference:
  reference=a.reference.read_bytes()
  if hashlib.sha1(reference).hexdigest()!=REFERENCE_SHA1:parser.error('Exact owner-supplied L5C reference required')
  older=bytearray(source);older[0x2AF98:0x2AFB4]=reference[0x2AF98:0x2AFB4]
  variants.append(('L5C_numeric_same_wrapper',bytes(older)))
 output=a.output.resolve();output.mkdir(parents=True,exist_ok=False);results=[]
 source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 for variant,owned_image in variants:
  folder=output/variant;folder.mkdir()
  fixture=bytearray(owned_image)
  # Select the logical bank and its native shadow, load caller D, enter the real hook.
  bootstrap=bytes.fromhex('1A50862AB73FFC9711FC0B107E6091')
  for start,data in [(0x7FB40,bootstrap),(0x7FB60,bytes.fromhex('20FE'))]:
   if fixture[start:start+len(data)]!=b'\xff'*len(data):raise ValueError('Fixture bootstrap region is occupied')
   fixture[start:start+len(data)]=data
  fixture=checksum(fixture)
  (folder/'UNIT_ONLY_NEVER_BURN.bin').write_bytes(fixture)
  rompath=folder/'PRIVATE-roms';game=rompath/'gw_kh5';game.mkdir(parents=True)
  (game/'getaw_kh5.rom').write_bytes(fixture);(game/'u18snd').write_bytes(sound)
  with emulator(a.emulator.resolve(),folder/'native',rompath,a.port) as api:
   def reg(name,value):api.call('debugger/state/write',reg=str(name),val=f'{value:X}')
   def mem(address,size):return api.call('debugger/memory',addr=f'{address:04X}',size=size)['data']
   def write(address,data,readback=True):
    api.call('debugger/memory/write',addr=f'{address:04X}',data=bytes(data).hex())
    if readback and mem(address,len(data))!=list(data):raise AssertionError('Synthetic RAM input readback differs')
   def cpu():return api.call('debugger/state')['cpus'][0]
   def wait_pause():
    deadline=time.monotonic()+10
    while not api.call('info')['paused']:
     if time.monotonic()>deadline:raise TimeoutError('Native execution did not return')
     time.sleep(.002)
   def break_at(address,bank=None):
    api.call('debugger/breakpoints',cmd='clear')
    args=dict(cmd='add',addr=f'{address:04X}')
    if bank is not None:args['bank']=bank
    api.call('debugger/breakpoints',**args)
   def run_to(address,bank=None):
    break_at(address,bank);api.call('debugger/control',cmd='resume');wait_pause()
    if cpu()['pc']!=address:raise AssertionError('Unexpected native stop')
   def step():
    previous=cpu()['pc'];api.call('debugger/breakpoints',cmd='clear')
    api.call('debugger/control',cmd='step');deadline=time.monotonic()+5
    while True:
     value=cpu()
     if value['pc']!=previous and api.call('info')['paused']:return value
     if time.monotonic()>deadline:raise TimeoutError('Instruction did not step')
     time.sleep(.002)
   def quiet():
    value=cpu();reg('CC',value['cc']|0x50);reg(11,0);reg(12,0)
    for address,data in [(0x3FFF,[0x80]),(0x3FF8,[0]),(0x3FBD,[0xFF])]:write(address,data,False)
   def semantic_inputs():
    return dict(counters=mem(0x0805,2),phase=mem(0x008C,3),game_phase=mem(0x17A4,1),
                scheduler_heads=mem(0x0366,2)+mem(0x0371,2),bank_shadow=mem(0x11,1))
   def equal_context(before,after,expected_cc):
    if any(before[key]!=after[key] for key in ['pc','sp','a','b','dp','x','y','u']):
     raise AssertionError(dict(kind='Register/stack context changed',before=before,after=after))
    # IRQ forces E=1 in its hardware frame; FIRQ forces E=0. E describes RTI frame
    # format and is not an arithmetic flag. Check every other CC bit exactly.
    if (after['cc']&0x7F)!=(expected_cc&0x7F):
     raise AssertionError(dict(kind='CC changed',expected=expected_cc,after=after['cc']))
   def inject(mode):
    quiet();before=cpu();inputs=semantic_inputs();bank=api.call('info')['wpc_bank']
    hardware_timer=mode=='TIMER_FIRQ'
    if hardware_timer:
     # Let the real timer expire while the CPU only executes a masked BRA loop.
     api.call('debugger/breakpoints',cmd='clear');reg('PC',0xFB60)
     write(0x3FF8,[1],False);api.frames(1)
     if not mem(0x3FF8,1)[0]&0x80:raise AssertionError('WPC high-resolution timer did not assert')
     reg('PC',before['pc'])
    nested=mode=='IRQ_WITH_NESTED_DMD_FIRQ';firq=mode in ['DMD_FIRQ','TIMER_FIRQ']
    desired=before['cc']&~(0x50 if nested else 0x40 if firq else 0x10)
    if not hardware_timer:reg(12 if firq else 11,1)
    reg('CC',desired);entry=cpu()
    if entry['pc']!=(0x8EEF if firq else 0xDC00):raise AssertionError('Interrupt vector was not entered')
    if entry['sp']!=before['sp']-(3 if firq else 12):raise AssertionError('Wrong hardware interrupt frame size')
    # These clear only the injected core line. The native handler still executes
    # and acknowledges its real ASIC source; timer status remains readable.
    reg(11,0);reg(12,0)
    if nested:
     reg(12,1);reg('CC',entry['cc']);inner=cpu()
     if inner['pc']!=0x8EEF or inner['sp']!=entry['sp']-3:raise AssertionError('Nested FIRQ frame missing')
     reg(12,0);run_to(0xDC00);equal_context(entry,cpu(),entry['cc'])
    run_to(before['pc'],'2A' if before['pc']<0x8000 else None)
    after=cpu();equal_context(before,after,desired)
    if semantic_inputs()!=inputs:raise AssertionError('Interrupt changed a guard input or bank shadow')
    if api.call('info')['wpc_bank']!=bank:raise AssertionError('Interrupt did not restore the selected ROM bank')
    active=mem(0x6F98,28)
    if bytes(active)!=fixture[0x2AF98:0x2AFB4]:raise AssertionError('Wrong physical code bank after interrupt')
    quiet()
    return dict(mode=mode,PC=f'{before["pc"]:04X}',result='PASS',hardware_frame_verified=True,
                context_preserved=True,guard_inputs_preserved=True,code_bank_preserved=True)
   api.frames(600);api.frames(600);api.button('10',after=1200)
   # Require the initialized native timer and DMD callback configuration we test.
   if mem(8,4)!=[0xDB,0xF2,0xEB,0x4A]:raise AssertionError('Unexpected active FIRQ callbacks')
   for name,q,live,task,d,pwm in SCENARIOS:
    quiet();write(0x0366,[0x0D,0] if task else [0,0]);write(0x0371,[0,0]);write(0x0059,[0,0])
    write(0x0D00,[0]*0x2D);write(0x0D11,[0,task]);write(0x0805,[q,live]);write(0x0B10,d.to_bytes(2,'big'))
    write(0x00E6,pwm.to_bytes(2,'big'));write(0x0F00,[0x7F,0xFF])
    for key,value in [('S',0x0F00),('DP',0),('X',0x1357),('Y',0x2468),('U',0x9ABC),('PC',0xFB40)]:reg(key,value)
    run_to(0x6091,'2A');checks=[];steps=0
    while cpu()['pc'] not in [0x6096,0x7FFF]:
     pc=cpu()['pc'];steps+=1
     if steps>100:raise AssertionError('Unexpected guard path')
     covered=pc==0x6091 or 0x6F98<=pc<0x6FB4 or 0x6FD0<=pc<0x6FE1 or 0x6EC6<=pc<0x6EDB or 0x86BF<=pc<=0x86CB
     if not covered:raise AssertionError(f'Unexpected guard/helper PC {pc:04X}')
     for mode in MODES:checks.append(inject(mode))
     if pc==0x86C8:run_to(0x86CB)
     else:step()
    final=cpu();admit=q!=0 and live==1 and task!=0xF2
    if final['pc']!=(0x6096 if admit else 0x7FFF) or final['sp']!=(0x0EFE if admit else 0x0F02):raise AssertionError('Final admission/stack contract changed')
    if (final['a']<<8|final['b'])!=d:raise AssertionError('Caller D changed')
    case=dict(variant=variant,name=name,qualified=q,live=live,synthetic_task=task,caller_D=f'{d:04X}',
              initial_PWM_timer=f'{pwm:04X}',result='PASS',instruction_boundaries=len(checks)//len(MODES),
              injection_cases=len(checks),admitted=admit,checks=checks)
    results.append(case);(output/'progress.json').write_text(json.dumps(results,indent=2)+'\n')
    print(f'{variant} {name}: {len(checks)} interrupt cases PASS',flush=True)
 summary=dict(result='PASS',date='2026-11-09',target=release['target'],verification_source_sha256=source_hash,
              emulator_sha256=hashlib.sha256(a.emulator.read_bytes()).hexdigest(),cases=results,
              injection_cases=sum(c['injection_cases'] for c in results),modes=MODES,
              native_handlers_unmodified=True,hardware_CPU_frames_verified=True,
              limits=['Isolated native unit fixtures, not gameplay or a hardware trial',
                      'IRQ/DMD injection uses debugger pending-line state; timer FIRQ uses emulated WPC timer',
                      'Tested at visited guard/wrapper/shared-predicate boundaries; scheduler search internals run without injections',
                      'Initialized timer and DMD callbacks only; no exhaustive arbitrary callback/NMI/device-fault interleavings',
                      'E flag is normalized because hardware selects IRQ/FIRQ frame format; other CC bits checked exactly'])
 (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(f'PASS: {summary["injection_cases"]} interrupt cases; released KH5 unchanged',flush=True)

if __name__=='__main__':main()

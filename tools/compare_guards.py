#!/usr/bin/env python3
"""Native, owner-local numeric guard differential; fixtures MUST NEVER be burned.

Reads the old guard from a user-supplied exact L5C image. No reference instruction
bytes are distributed. The batch controller executes both guards on PinMAME's
6809, retaining the real native game-state predicate. Only its continuation is
redirected to collect results. IRQ/FIRQ are masked; this is not gameplay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from kh5patch.core import identity
from replay import emulator

REFERENCE_SHA1='16e83bc01c452781150275a0e88a71072cf9bc43'

class Program:
 def __init__(self):self.start=0x7100;self.code=bytearray();self.labels={};self.fixups=[]
 def label(self,name):self.labels[name]=self.start+len(self.code)
 def emit(self,*values):self.code.extend(values)
 def word(self,value):self.code.extend(value.to_bytes(2,'big'))
 def ext(self,opcode,operand):
  self.emit(opcode)
  if isinstance(operand,str):self.fixups.append((len(self.code),operand,False));self.word(0)
  else:self.word(operand)
 def branch(self,condition,label):
  self.emit(0x10,condition);self.fixups.append((len(self.code),label,True));self.word(0)
 def finish(self):
  for offset,label,relative in self.fixups:
   value=self.labels[label]-(self.start+offset+2) if relative else self.labels[label]
   self.code[offset:offset+2]=(value&65535).to_bytes(2,'big')
  return bytes(self.code)

def controller(pending_wrapper=False):
 p=Program()
 def load_a(address):p.ext(0xB6,address)
 def store_a(address):p.ext(0xB7,address)
 def immediate_a(value):p.emit(0x86,value)
 def jump(label):p.ext(0x7E,label)
 def set_inputs():
  p.emit(0x10,0xCE);p.word(0x0F00) # LDS #$0F00, unprotected unit stack
  p.emit(0x8E);p.word(0x1357) # X
  p.emit(0x10,0x8E);p.word(0x2468) # Y
  p.emit(0xCE);p.word(0x9ABC) # U
  load_a(0x0B10);p.emit(0x34,0x02) # save requested CC temporarily
  p.ext(0xFC,0x0B11) # LDD requested caller D
  p.emit(0x35,0x01) # PULS CC; restores requested flags after setup loads
 p.label('start');p.emit(0x1A,0x50,0x4F,0x1F,0x8B) # mask interrupts; DP=0
 for address in [0x0B00,0x0B01,0x0B04,0x0B05,0x0B06,0x0B0F]:p.ext(0x7F,address)
 p.label('vector')
 load_a(0x0B00);store_a(0x0805);load_a(0x0B01);store_a(0x0806)
 p.ext(0x7F,0x0B20) # stage=reference
 set_inputs();p.ext(0xBD,0x6FD0 if pending_wrapper else 0x6F98) # user-owned Soren routine
 p.emit(0x34,0x7F) # snapshot CC,D,DP,X,Y,U before changing flags/registers
 immediate_a(0);store_a(0x0B21);jump('reference_capture')
 p.label('accepted');p.emit(0x34,0x7F)
 immediate_a(1);store_a(0x0B21)
 load_a(0x0B20);p.branch(0x26,'candidate_capture');jump('reference_capture')
 p.label('reference_capture')
 p.emit(0x10,0xFF);p.word(0x0B30) # STS reference snapshot pointer
 # Snapshot D must equal caller D, not just match another implementation.
 p.emit(0xEC,0x61) # LDD 1,S
 p.emit(0x10,0xB3);p.word(0x0B11);p.branch(0x26,'failed') # CMPD caller D
 load_a(0x0B21);store_a(0x0B32)
 # Accepted frame retains saved D directly above the 10-byte snapshot.
 p.branch(0x27,'reference_copy')
 p.emit(0xEC,0x6A,0x10,0xB3);p.word(0x0B11);p.branch(0x26,'failed')
 p.label('reference_copy')
 p.emit(0x8E);p.word(0x0B40);p.emit(0x1F,0x42,0xC6,10) # X=record, Y=S
 p.label('copy');p.emit(0xA6,0xA0,0xA7,0x80,0x5A);p.branch(0x26,'copy')
 immediate_a(1);store_a(0x0B20)
 set_inputs();p.ext(0xBD,0x7030 if pending_wrapper else 0x7000) # exact KH5 numeric routine, relocated only in fixture
 p.emit(0x34,0x7F);immediate_a(0);store_a(0x0B21);jump('candidate_capture')
 p.label('candidate_capture')
 p.emit(0x10,0xFF);p.word(0x0B34) # STS candidate snapshot pointer
 p.ext(0xFC,0x0B30);p.emit(0x10,0xB3);p.word(0x0B34);p.branch(0x26,'failed')
 load_a(0x0B21);p.ext(0xB1,0x0B32);p.branch(0x26,'failed')
 # Independently require the correct admission predicate for all byte values.
 if pending_wrapper:
  load_a(0x0B13);p.emit(0x81,0xF2);p.branch(0x27,'expect_reject')
 load_a(0x0B00);p.branch(0x27,'expect_reject')
 load_a(0x0B01);p.emit(0x81,1);p.branch(0x26,'expect_reject')
 load_a(0x0B21);p.emit(0x81,1);p.branch(0x26,'failed')
 p.emit(0xEC,0x6A,0x10,0xB3);p.word(0x0B11);p.branch(0x26,'failed')
 jump('compare')
 p.label('expect_reject');load_a(0x0B21);p.branch(0x26,'failed')
 p.label('compare')
 p.emit(0x8E);p.word(0x0B40);p.emit(0x1F,0x42,0xC6,10)
 p.label('compare_byte');p.emit(0xA6,0x80,0xA1,0xA0);p.branch(0x26,'failed')
 p.emit(0x5A);p.branch(0x26,'compare_byte')
 # Independent three-byte count, then enumerate all 256 x 256 combinations.
 p.ext(0x7C,0x0B06);p.branch(0x26,'next_vector');p.ext(0x7C,0x0B05)
 p.branch(0x26,'next_vector');p.ext(0x7C,0x0B04)
 p.label('next_vector');p.ext(0x7C,0x0B01);p.branch(0x26,'vector')
 p.ext(0x7C,0x0B00);p.branch(0x26,'vector')
 immediate_a(1);store_a(0x0B0F);jump(0x7FFF)
 p.label('failed');immediate_a(255);store_a(0x0B0F);jump(0x7FFF)
 return p.finish(),p.labels

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for option in ['emulator','rom','reference','sound','output']:parser.add_argument('--'+option,type=Path,required=True)
 parser.add_argument('--port',type=int,default=9052)
 parser.add_argument('--pending-wrapper',action='store_true',help='Compare both numeric guards behind the same KH5 pending-F2 wrapper')
 parser.add_argument('--negative-control',action='store_true',help='Require detection of a deliberately broken disposable candidate guard')
 a=parser.parse_args();source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 meta=json.loads((ROOT/'patches/release.json').read_text());candidate=a.rom.read_bytes();reference=a.reference.read_bytes();sound=a.sound.read_bytes()
 if identity(candidate)!=meta['target']:parser.error('Exact qualified KH5 image required')
 if hashlib.sha1(reference).hexdigest()!=REFERENCE_SHA1:parser.error('Exact privately supplied L5C reference required')
 if hashlib.sha1(sound).hexdigest()!='e6b7ccef250db0c801e3dd8ebf93522b466ca1ec':parser.error('Matching private U18 required')
 if reference[0x2AEC6:0x2AEDB]!=candidate[0x2AEC6:0x2AEDB]:parser.error('Native predicate differs')
 output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
 code,labels=controller(a.pending_wrapper);fixture=bytearray(candidate)
 if fixture[0x2B100:0x2B100+len(code)]!=b'\xff'*len(code):parser.error('Batch controller region is not baseline free space')
 if fixture[0x7FB40:0x7FB48]!=b'\xff'*8:parser.error('Bootstrap region is not free space')
 fixture[0x2AF98:0x2AFB4]=reference[0x2AF98:0x2AFB4]
 fixture[0x2B000:0x2B019]=candidate[0x2AF98:0x2AFB1]
 if a.pending_wrapper:
  fixture[0x2B030:0x2B041]=candidate[0x2AFD0:0x2AFE1]
  fixture[0x2B03B:0x2B03E]=bytes.fromhex('7E7000')
 if a.negative_control:
  if fixture[0x2B00B]!=0x26:raise AssertionError('Unexpected candidate branch')
  fixture[0x2B00B]=0x20 # Own disposable candidate: force the live-count reject branch
 fixture[0x2B100:0x2B100+len(code)]=code
 fixture[0x2A096:0x2A099]=bytes([0x7E])+labels['accepted'].to_bytes(2,'big')
 fixture[0x7FB40:0x7FB48]=bytes.fromhex('862AB73FFC7E7100')
 (output/'UNIT_ONLY_NEVER_BURN.bin').write_bytes(fixture)
 rompath=output/'PRIVATE-roms';game=rompath/'gw_kh5';game.mkdir(parents=True)
 (game/'getaw_kh5.rom').write_bytes(fixture);(game/'u18snd').write_bytes(sound)
 profiles=[(0x0000,0x50,[0,0,0,0]),(0xFFFF,0x51,[1,0,0,0]),
           (0x1234,0x52,[0,0x80,0,0]),(0x80FF,0x54,[0,0,255,0]),
           (0x7F00,0x58,[0,0,0,1]),(0x00FF,0x70,[255,255,255,255]),
           (0xFF00,0xD0,[0,0,0,0]),(0xA55A,0xFF,[0x80,0,0,0])]
 if a.pending_wrapper:
  profiles=[(0x1234,0x50,[0,0,0,0]),(0x1234,0x51,[0,0x80,0,0]),(0xA55A,0xFF,[255,255,255,255])]
 if a.negative_control:profiles=profiles[:1]
 rows=[]
 with emulator(a.emulator.resolve(),output/'native',rompath,a.port) as api:
  def write(address,data):
   api.call('debugger/memory/write',addr=f'{address:04X}',data=bytes(data).hex())
   if api.call('debugger/memory',addr=f'{address:04X}',size=len(data))['data']!=list(data):raise AssertionError('Synthetic input readback mismatch')
  api.call('debugger/breakpoints',cmd='clear');api.call('debugger/watchpoints',cmd='clear')
  api.call('debugger/breakpoints',cmd='add',addr='7FFF',bank='2A')
  # Verify the executable fixture, including both privately loaded routines.
  for address,offset,length,bank in [(0x6F98,0x2AF98,28,'2A'),(0x7000,0x2B000,25,'2A'),(0x7100,0x2B100,len(code),'2A')]:
   if bytes(api.call('debugger/memory',addr=f'{address:04X}',size=length,bank=bank)['data'])!=fixture[offset:offset+length]:raise AssertionError('Loaded fixture differs')
  for index,(d,cc,phase) in enumerate(profiles):
   task=[0,0xF2,0xF3][index] if a.pending_wrapper else 0
   write(0x0B13,[task])
   if a.pending_wrapper:
    write(0x0366,[0x0D,0] if task else [0,0]);write(0x0371,[0,0]);write(0x0059,[0,0])
    write(0x0D00,[0]*0x2D);write(0x0D11,[0,task])
   write(0x0B10,bytes([cc])+d.to_bytes(2,'big'));write(0x008C,phase[:3]);write(0x17A4,[phase[3]])
   for name,val in [('CC',0x50),('DP',0),('S',0x0F00),('PC',0xFB40)]:api.call('debugger/state/write',reg=name,val=f'{val:X}')
   api.call('debugger/control',cmd='resume');deadline=time.monotonic()+180
   while not api.call('info')['paused']:
    if time.monotonic()>deadline:raise TimeoutError('Batch controller did not complete')
    time.sleep(.2)
   data=api.call('debugger/memory',addr='0B00',size=0x50)['data']
   count=int.from_bytes(bytes(data[4:7]),'big')
   if a.negative_control:
    if (data[15],count,data[0],data[1])!=(255,257,1,1):raise AssertionError('Negative control did not detect the known admission error')
   elif data[15]!=1 or count!=65536:raise AssertionError(dict(profile=index,qualified=data[0],live=data[1],status=data[15],completed=count))
   rows.append(dict(profile=index,initial_D=f'{d:04X}',initial_CC=f'{cc:02X}',native_phase=phase,synthetic_task=task,compared_vectors=count,result='PASS: injected fault detected' if a.negative_control else 'PASS'))
   print('Negative control: detected admission error at qualified=1, live=1' if a.negative_control else f'Profile {index+1}/{len(profiles)}: {count} native differential vectors PASS',flush=True)
 summary=dict(result='PASS',verification_source_sha256=source_hash,pending_wrapper=a.pending_wrapper,negative_control=a.negative_control,target=meta['target'],reference_sha1=REFERENCE_SHA1,fixture_sha256=hashlib.sha256(fixture).hexdigest(),emulator_sha256=hashlib.sha256(a.emulator.read_bytes()).hexdigest(),profiles=rows,compared_vectors=sum(r['compared_vectors'] for r in rows),guard_invocations=2*(sum(r['compared_vectors'] for r in rows)+(1 if a.negative_control else 0)),qualified_range=[0,255],live_range=[0,255],checked=['admission vs reference and independent predicate','CC including carry/overflow/negative/zero','D, DP, X, Y, U','stack pointer at return/continuation','accepted saved-D stack frame'],native_predicate_retained=True,IRQs_and_FIRQs_masked=True,scope='Numeric guard comparison; pending wrapper, when enabled, is identical on both sides and retains native task lookup; not equality to unmodified L5C as a whole',limits=['Not cycle-identical; different instruction counts and scratch-stack writes','No interrupt arrival interleavings or arbitrary corrupt scheduler simulation','Caller DP=0; normal game contract','Unit fixture, not gameplay; NEVER BURN'])
 (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()

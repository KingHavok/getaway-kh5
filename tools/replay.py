#!/usr/bin/env python3
"""Replay ROM-free scenarios in a fresh, local, source-built research PinMAME.

Game/sound inputs and raw outputs remain in the supplied private output directory.
Public oracles contain scalar state and native callback counts, never RAM dumps.
"""
import argparse,contextlib,hashlib,json,os,pathlib,shutil,subprocess,time,urllib.parse,urllib.request,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from kh5patch.core import identity

class API:
 def __init__(self,port):self.port=port;self.frames_executed=0
 def raw(self,path,**params):
  with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/api/'+path+'?'+urllib.parse.urlencode(params),timeout=20) as f:return f.read()
 def call(self,path,**params):
  data=json.loads(self.raw(path,**params))
  if data.get('status')=='error':raise RuntimeError(data.get('message','Debugger rejected request'))
  return data
 def frames(self,count):
  self.call('debugger/control',cmd='frames',count=count);deadline=time.monotonic()+60
  while True:
   info=self.call('info')
   if info['paused']:
    if info['frames_remaining']:raise ValueError('Unexpected early breakpoint')
    self.frames_executed+=count;return info
   if time.monotonic()>deadline:raise TimeoutError('Frame request not completed')
   time.sleep(.01)
 def button(self,mask,on=6,after=0):
  self.call('input/button',mask=mask,val=1);self.frames(on);self.call('input/button',mask=mask,val=0)
  while after:n=min(after,600);self.frames(n);after-=n

@contextlib.contextmanager
def emulator(binary,folder,rompath,port,seed=None):
 folder.mkdir(parents=True,exist_ok=False);api=API(port)
 try:api.call('info')
 except OSError:pass
 else:raise ValueError('Debugger port already in use')
 nv=folder/'nvram';nv.mkdir()
 if seed:shutil.copyfile(seed,nv/'gw_kh5.nv')
 command=[str(binary),'-headless','-startpaused','-httpport',str(port),'-nosound','-fakesound','-nocheat','-skip_disclaimer','-skip_gameinfo','-skip_gamewarnings','-rtc','2026-11-08 12:00:00','-rompath',str(rompath)]
 for option,name in [('nvram','nvram'),('cfg','cfg'),('memcard','mem'),('input','inp'),('hiscore','hi'),('state','sta'),('snapshot','snap'),('diff','diff')]:
  directory=folder/name;directory.mkdir(exist_ok=True);command+=['-'+option+'_directory',str(directory)]
 command+=['gw_kh5'];env=dict(os.environ,PINMAME_WORK_HOME=str(folder),GETAWAY_TEST_ENABLE='1',GETAWAY_IO_TRACE=str(folder/'PRIVATE-coils.jsonl'))
 with (folder/'PRIVATE-emulator.log').open('w') as log:
  proc=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT)
  try:
   deadline=time.monotonic()+30
   while True:
    try:
     if api.call('info')['game']!='gw_kh5':raise ValueError('Wrong game on port')
     break
    except OSError:
     if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Emulator did not start; inspect PRIVATE-emulator.log')
     time.sleep(.1)
   yield api
  finally:
   if proc.poll() is None:
    try:api.call('debugger/control',cmd='exit')
    except OSError:pass
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=5)

SCALARS={'008C':[0,1,2],'040F':[0,1],'0928':[0,4],'092C':[0],'0806':[0],'0800':[5,6],'0000':[0x8c,0x8d,0x8e,0x40f,0x410],'0903':[p*54+f for p in range(4) for f in [37,41]]}
POINTS={0x6253,0x537a,0x5200,0x45a4,0x56cb,0x56f3,0x5730,0x5776,0x4654,0x6098}
def observation(action,data):
 if action.get('path')=='/api/debugger/instrument' and not action.get('params'):
  return dict(kind='native_counts',counts={f'{p["bank"]:02X}:{p["addr"]:04X}':p['count'] for p in data['points'] if p['addr'] in POINTS})
 if action.get('path')=='/api/debugger/memory':
  address=action['params']['addr'].upper()
  if address in SCALARS:return dict(kind='scalar_state',address=address,values={str(i):data['data'][i] for i in SCALARS[address] if i<len(data['data'])})
 return None

def replay(api,script,folder):
 observed=[];actions=json.loads(script.read_text())
 with (folder/'PRIVATE-actions.jsonl').open('w') as log:
  for action in actions:
   if 'frames' in action:
    info=api.frames(action['frames']);data=dict(completed_frames=action['frames'])
   elif 'assert_memory' in action:
    expected=action['assert_memory'];params=dict(addr=expected['addr'],size=len(expected['data']))
    if 'bank' in expected:params['bank']=expected['bank']
    data=api.call('debugger/memory',**params)
    if data['data']!=expected['data']:raise AssertionError('Scenario state assertion at '+expected['addr'])
   else:
    if not action['path'].startswith('/api/'):raise ValueError('Only local API routes are permitted')
    raw=api.raw(action['path'][5:],**action.get('params',{}))
    try:data=json.loads(raw)
    except (ValueError,UnicodeDecodeError):data=dict(private_binary_bytes=len(raw))
    if isinstance(data,dict) and data.get('status')=='error':raise ValueError('Debugger action rejected')
    if 'save' in action:
     dest=folder/action['save']
     if not dest.resolve().is_relative_to(folder.resolve()):raise ValueError('Capture outside private output')
     dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    item=observation(action,data)
    if item:observed.append(item)
   log.write(json.dumps(dict(action=action,response=data))+'\n');log.flush()
 return observed

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--emulator',type=pathlib.Path,required=True);p.add_argument('--rom',type=pathlib.Path,required=True);p.add_argument('--sound',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--case',default='all');p.add_argument('--port',type=int,default=9050);a=p.parse_args()
 meta=json.loads((ROOT/'patches/release.json').read_text());image=a.rom.read_bytes();sound=a.sound.read_bytes()
 if identity(image)!=meta['target']:p.error('Supply the exact locally converted KH5 image')
 if hashlib.sha1(sound).hexdigest()!='e6b7ccef250db0c801e3dd8ebf93522b466ca1ec':p.error('Supply the matching production U18 sound ROM; it is never downloaded')
 output=a.output.resolve();output.mkdir(parents=True,exist_ok=False);rompath=output/'PRIVATE-roms';game=rompath/'gw_kh5';game.mkdir(parents=True)
 (game/'getaw_kh5.rom').write_bytes(image);(game/'u18snd').write_bytes(sound)
 with emulator(a.emulator.resolve(),output/'native-initialize',rompath,a.port) as api:
  api.frames(600);api.frames(600);api.button('10',after=1200)
 seed=output/'native-initialize/nvram/gw_kh5.nv';cases=json.loads((ROOT/'tests/scenarios.json').read_text());oracles=json.loads((ROOT/'tests/oracles.json').read_text());rows=[]
 selected=[c for c in cases if a.case=='all' or c['name']==a.case]
 if not selected:p.error('Unknown scenario name')
 for case in selected:
  folder=output/case['name']
  with emulator(a.emulator.resolve(),folder,rompath,a.port,seed) as api:
   seen=replay(api,ROOT/case['script'],folder)
   if seen!=oracles[case['name']]:raise AssertionError('Scalar/count oracle differs; preserve private outputs for investigation, do not count as PASS')
   rows.append(dict(case=case['name'],result='PASS',frames=api.frames_executed,script_sha256=hashlib.sha256((ROOT/case['script']).read_bytes()).hexdigest()))
  print(case['name']+': PASS',flush=True)
 summary=dict(image=meta['target'],emulator_sha256=hashlib.sha256(a.emulator.read_bytes()).hexdigest(),cases=rows,scope='Named scenarios with embedded state assertions and public scalar/count oracles; no full-game exhaustive or electrical-safety claim')
 (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if __name__=='__main__':main()

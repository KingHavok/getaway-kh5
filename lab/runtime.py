"""Owned emulator sessions for released, official and explicitly registered images."""
import contextlib,hashlib,json,shutil,sys,contextvars
from pathlib import Path
from .config import REPO,verify_image,sound,sha
sys.path.insert(0,str(REPO/'tools'))
from replay import emulator,API as Transport
PROJECT=None
TARGET='kh5'
LAB=None
_ROM_CACHE={}
ACTIVE=contextvars.ContextVar('getaway_image',default=None)
ROOT=REPO

def configure_project(project,target='kh5'):
 global PROJECT,TARGET,LAB
 PROJECT=project;TARGET=target;LAB=Path(project['workspace'])/'results';verify_image(project,target)

def selected(name=None):
 if PROJECT is None:raise RuntimeError('Use tools/lab.py to configure the private project')
 return name or ACTIVE.get() or TARGET

def owner_rom(name='l5'):
 entry,data=verify_image(PROJECT,name)
 return data

class OwnerView:
 def __init__(self,name,start=0,end=None):self.name=name;self.start=start;self.end=end
 def __getitem__(self,key):
  cache_key=(PROJECT['workspace'],self.name)
  if cache_key not in _ROM_CACHE:_ROM_CACHE[cache_key]=owner_rom(self.name)
  return _ROM_CACHE[cache_key][self.start:self.end][key]

def owner_view(name='l5',start=0,end=None):return OwnerView(name,start,end)

def image_path(name=None):return Path(verify_image(PROJECT,selected(name))[0]['path'])

def prepare(name=None,port=9070):
 from .driver import ensure
 name=selected(name);entry,data=verify_image(PROJECT,name);snd=sound(PROJECT)
 if not PROJECT.get('emulator'):raise ValueError('Build the emulator first with lab.py build')
 ensure(PROJECT,name)
 cache=Path(PROJECT['workspace'])/'prepared'/entry['driver']/entry['identity']['sha256']
 manifest=cache/'prepared.json'
 if manifest.exists():
  record=json.loads(manifest.read_text())
  for field in ['rom','sound','seed']:
   if sha(record[field])!=record[field+'_sha256']:raise ValueError('Prepared private input changed')
  if record['image']!=entry['identity'] or record['driver']!=entry['driver']:raise ValueError('Prepared image/driver identity differs')
  return record
 cache.mkdir(parents=True,exist_ok=False);rompath=cache/'roms';game=rompath/entry['driver'];game.mkdir(parents=True)
 rom=game/entry['filename'];rom.write_bytes(data);sound_file=game/'u18snd';sound_file.write_bytes(snd)
 with emulator(Path(PROJECT['emulator']),cache/'initialize',rompath,port,driver=entry['driver']) as api:
  api.frames(600);api.frames(600);api.button('10',after=1200)
 seed=cache/'initialize/nvram'/(entry['driver']+'.nv')
 if not seed.exists():raise ValueError('Native initialization did not produce NVRAM')
 record=dict(image=entry['identity'],driver=entry['driver'],rompath=str(rompath),rom=str(rom),sound=str(sound_file),seed=str(seed),
  rom_sha256=sha(rom),sound_sha256=sha(sound_file),seed_sha256=sha(seed),emulator_sha256=sha(PROJECT['emulator']))
 manifest.write_text(json.dumps(record,indent=2)+'\n');return record

@contextlib.contextmanager
def select(name):
 token=ACTIVE.set(name)
 try:yield
 finally:ACTIVE.reset(token)

@contextlib.contextmanager
def session(folder,port,source,game=None,instrumented=True,nvram_seed=None,sound_cpu=True,unit=False):
 from .api import API
 name=selected();entry,data=verify_image(PROJECT,name)
 prepared=prepare(name,port);folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
 seed=Path(nvram_seed) if nvram_seed else Path(prepared['seed']);original_seed=seed.read_bytes()
 record=dict(result='FAIL: investigate',image_name=name,game=entry['driver'],controller_role=game,
  image_sha1=entry['identity']['sha1'],image_sha256=entry['identity']['sha256'],rom_file=entry['path'],
  emulator_sha256=sha(PROJECT['emulator']),test_source_sha256=sha(source),session_source_sha256=sha(__file__),
  initial_nvram_sha256=sha(seed),nvram_seed_path=str(seed),fresh_process=True,sound_cpu_enabled=True,
  native_initialized_seed=True,layout=entry['layout'],unit=unit,workflow_sources={str(p.relative_to(REPO)):sha(p) for directory in ['lab','research'] for p in sorted((REPO/directory).glob('*.py'))},seed_initializer_emulator_sha256=prepared['emulator_sha256'],rtc='2026-11-08 12:00:00')
 (folder/'launch.json').write_text(json.dumps(record,indent=2)+'\n')
 (folder/'emulator.run.json').write_text(json.dumps(record,indent=2)+'\n')
 api=None
 try:
  with (folder/'actions.jsonl').open('w') as log:
   # Same owned transport as the public replay runner, with explicit driver/NV name.
   # The raw output filename is retained for the historical coil analyzer.
   with emulator(Path(PROJECT['emulator']),folder/'runtime',Path(prepared['rompath']),port,seed,driver=entry['driver'],io_trace=folder/'raw-coils.jsonl') as transport:
    api=API(port,log,unit=unit)
    record["command"]=transport.command
    initial=api.io()
    if not initial["enabled"] or any(s["forced"]!=-1 for s in initial["switches"]) or initial["mechanisms"]:raise AssertionError("Fault instrumentation is not neutral at session start")
    try:
     yield api,record
     if record.get('result') not in ['PASS','OBSERVED','EXPLORATION']:raise AssertionError('Controller did not establish a declared result')
    finally:
     record['frames']=api.frames_run
     record['final_io']=api.io()
 except Exception as error:
  record.update(result='FAIL: investigate',error=str(error),exception=type(error).__name__)
  raise
 finally:
  record['source_nvram_unchanged']=seed.read_bytes()==original_seed
  final=folder/'runtime/nvram'/(entry['driver']+'.nv')
  if final.exists():record['final_nvram_sha256']=sha(final)
  (folder/'result.json').write_text(json.dumps(record,indent=2)+'\n')

# Function imports are deferred to avoid cycles in the historical controller ports.
def configure(api,values):
 from readiness_session import configure as fn
 return fn(api,values)
def qualify_locks(*args,**kwargs):
 from readiness_session import qualify_locks as fn
 return fn(*args,**kwargs)
def collect_lock(*args,**kwargs):
 from readiness_session import collect_lock as fn
 return fn(*args,**kwargs)
def launch_and_validate(*args,**kwargs):
 from readiness_session import launch_and_validate as fn
 return fn(*args,**kwargs)
def ensure_playable(*args,**kwargs):
 from readiness_multiplayer import ensure_playable as fn
 return fn(*args,**kwargs)
def wait_saver(*args,**kwargs):
 from readiness_multiplayer import wait_saver as fn
 return fn(*args,**kwargs)
def drain_turn(*args,**kwargs):
 from readiness_multiplayer import drain_turn as fn
 return fn(*args,**kwargs)
def installed(io):return [b for b in io['balls'] if b['installed']]
def setup(api,players=1,extended=False):
 api.frames(1200)
 configure(api,{0x1B1F:5 if extended else 3,0x1B21:1,0x1B23:0,0x1B39:3,0x1B43:0,0x1B51:1,
  0x1B5F:0,0x1B61:0,0x1B9D:1,0x1BBF:0,0x1BC9:0,0x1BCB:99 if extended else 20,0x1BD3:20,0x1BD5:99 if extended else 20})
 api.call('debugger/tracepoints',cmd='clear')
 for addr,bank in [('6253','2A'),('6A88','2A'),('56CB','2A'),('481A','30')]:api.call('debugger/tracepoints',cmd='add',addr=addr,bank=bank)
 api.button('200',after=300)
 for _ in range(players-1):api.button('200',after=120)
 if api.memory(0x17A5,1)!=bytes([players]):raise AssertionError('Native player count did not match setup')
def observe(api,seconds,activity=False):
 samples=[]
 for index in range(seconds):
  if activity and index%4==0:
   api.call('input',sw=31,val=1);api.frames(6);api.call('input',sw=31,val=0);api.frames(54)
  else:api.frames(60)
  item=api.marker(f'observe-{index+1}');samples.append(item)
  if len(installed(item['io']))!=3:raise AssertionError('Physical installed-ball inventory changed')
 return samples

"""Replay an owned B6 external-input ledger without recomputing its shot timings."""
import json,hashlib,time
from pathlib import Path
from . import runtime
from .config import private_path

def run(project,image,ledger,output,port):
 from b6_reproduce_v5 import Experiment
 ledger=Path(ledger).resolve();items=json.loads(ledger.read_text());folder=private_path(output)
 with runtime.select(image),runtime.session(folder,port,__file__) as (api,record):
  experiment=Experiment(api,folder,replay=True)
  for item in items:
   if 'checkpoint' in item:experiment.snapshot(item['checkpoint']);continue
   path=item['path'];params=item['params']
   if not (path.startswith('input') or path in ['debugger/control','debugger/memory/write','debugger/tracepoints']):raise ValueError('Unsupported ledger mutation')
   if path=='debugger/control':
    if params.get('cmd')!='frames' or not 0<params['count']<=3600:raise ValueError('Only bounded frame requests may be replayed')
   api.call(path,**params)
   if path=='debugger/control':
    deadline=time.monotonic()+60
    while not api.call('info')['paused']:
     if time.monotonic()>deadline:raise TimeoutError('Ledger frame budget incomplete')
     time.sleep(.01)
    if api.call('info')['frames_remaining']:raise AssertionError('Ledger stopped early')
    api.frames_run+=params['count']
  record.update(result='OBSERVED',qualification='Exact stimulus replay; compare observations, not an automatic bug-free pass',
   stimulus_sha256=hashlib.sha256(ledger.read_bytes()).hexdigest(),checkpoints=len(experiment.snapshots))
 from .driver import check_log
 check_log(folder/'runtime/PRIVATE-emulator.log')
 result=dict(result='OBSERVED',image_name=image,image_sha256=record['image_sha256'],stimulus_sha256=record['stimulus_sha256'],frames=record['frames'],checkpoints=record['checkpoints'])
 (folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result

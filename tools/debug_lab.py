#!/usr/bin/env python3
"""Open a private native debugger session; it never qualifies as a gameplay pass.

Supply JSON lines {"path":"debugger/memory","params":{"addr":"0805","size":2}}
or {"frames":120}; {"finish":true} ends the owned session. All responses stay in
its private log as well as stdout. Do not post raw debugger output publicly.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'research'))
from lab import config,runtime
from lab.locking import acquire
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--image',default='kh5');p.add_argument('--output',type=Path,required=True);p.add_argument('--port',type=int,default=9070);a=p.parse_args()
x=config.load(a.project);runtime.configure_project(x,a.image);lease=acquire(x)
try:
 with runtime.session(config.private_path(a.output),a.port,__file__,unit=True) as (api,r):
  api.frames(1200);print(json.dumps(dict(status='EXPLORATION',URL=f'http://127.0.0.1:{a.port}/',image=x['images'][a.image]['identity'])),flush=True)
  for line in sys.stdin:
   command=json.loads(line)
   if command.get('finish'):break
   if 'frames' in command:api.frames(command['frames']);print(json.dumps(api.state()),flush=True)
   else:print(json.dumps(api.call(command['path'],**command.get('params',{}))),flush=True)
  r.update(result='EXPLORATION',qualification='Unqualified interactive debugger session; CPU/RAM mutations permitted, never a gameplay regression pass')
finally:lease.close()

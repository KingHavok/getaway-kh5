"""Authored matched replay/knocker controls, ported from readiness_knocker.
Uses only published inputs and numeric settings; captures remain owner-local.
"""
import json,hashlib
from . import runtime
from .config import REPO
from .replay import actions

def run(folder,port,award):
 script=json.loads((REPO/'research/inputs/core_a1_cold.json').read_text());out=[];inserted=False
 def request(path,**params):return {'path':'/api/'+path,'params':params}
 for action in script:
  path=action.get('path','');params=action.get('params',{})
  if path.startswith('/api/debugger/dmdrec') or path=='/api/monitor' and params.get('cmd') in ['clear','add']:continue
  if not inserted and path=='/api/input/button' and params=={'mask':'200','val':1}:
   settings={0x1B1F:5,0x1B27:1,0x1B2D:1,0x1B2F:0x10,0x1B37:0,0x1B39:award}
   out.append(request('debugger/memory/write',addr='3FFD',data='B4'))
   out.extend(request('debugger/memory/write',addr=f'{a:04X}',data=f'{v:04X}') for a,v in settings.items())
   out.append(request('debugger/memory/write',addr='3FFD',data='00'))
   out.extend({'assert_memory':{'addr':f'{a:04X}','data':list(v.to_bytes(2,'big'))}} for a,v in settings.items())
   out.extend([request('monitor',cmd='clear'),request('monitor',cmd='add',type='sol',id=7)])
   inserted=True
  out.append(action)
 if not inserted:raise AssertionError('Replay setup never reached native start')
 out.append(request('monitor/log'))
 with runtime.session(folder,port,__file__) as (api,r):
  private=folder/'stimulus.json';private.write_text(json.dumps(out,indent=2)+'\n');events=[]
  actions(api,private,folder,events=events)
  monitor=[e['response'] for e in events if e['action'].get('path')=='/api/monitor/log'][-1]
  pulses=[x for x in monitor['actions'] if x['type']=='sol' and x['id']==7 and x['val']]
  if bool(pulses)!=(award==0):raise AssertionError('Matched replay/knocker award expectation failed')
  r.update(result='PASS',replay_award=award,knocker_activations=len(pulses),script_sha256=hashlib.sha256(private.read_bytes()).hexdigest(),
   qualification='Matched five-ball/free-play replay threshold flow, positive credit award versus audit-only; not every knocker source')

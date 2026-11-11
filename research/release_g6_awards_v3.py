"""Port of authored historical controller release_g6_awards_v3. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import hashlib,json

from release_g6_lab_v2 import BASE,session,adapt,configure,trace,save_trace,dmd

from readiness_multiplayer import ensure_playable

from b6_reproduce_v5 import wait_no_saver
from lab.config import REPO as ROOT
from lab.runtime import owner_view
from types import SimpleNamespace


def run_case(folder,port,spec):
 kids=spec.get("kids",False)
 source=__import__('pathlib').Path(ROOT/'research/inputs/g5sm_success_launched.json')
 actions=json.loads(source.read_text())
 with session(folder,port,__file__,game='gw_g6',sound_cpu=True) as (api,r):
   adapt(api);api.frames(1200)
   configure(api,{0x1B9D:1,0x1B51:1,0x1B23:4,0x1B25:0,0x1BBF:35,0x1B39:3,0x1B43:0,0x1BC9:0})
   trace(api,[(0x56CB,0x2A),(0x5730,0x2A),(0x5776,0x2A)])
   api.call('debugger/tracepoints',cmd='add',addr='B4C4')
   samples=[]
   for i,a in enumerate(actions[18:],18):
    if 'frames' in a:api.frames(a['frames'])
    elif a.get('path','').startswith('/api/input'):api.call(a['path'][5:],**a.get('params',{}))
    elif a.get('path')=='/api/dmd/pnm':
     samples.append(dict(index=i,counters=api.memory(0x40f,10).hex(),lights=api.memory(0x2e0,96).hex(),challenge=api.memory(0x8e0,8).hex()))
     dmd(api,folder,f'legacy-{i}')
   before=api.marker('nine-targets-complete-before-tunnel')
   from pilot_burn_rubber import tunnel
   api.pulse(4,'800',after=600)
   after=api.marker('tunnel-award-collected')
   log=save_trace(api,folder,'native-awards')
   (folder/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')
   print('COUNTERS',api.memory(0x40f,10).hex(),'TRACE',[(hex(t['pc']),t['bank']) for t in log],flush=True)
   dmd(api,folder,'finished');r.update(result='PASS',before_collection=before,after_collection=after,qualification='Native award probe; independent contract audit pending',legacy_script_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),samples=samples)

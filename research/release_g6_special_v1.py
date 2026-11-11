"""Port of authored historical controller release_g6_special_v1. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
from lab.runtime import owner_view
import json

from release_g6_lab_v2 import BASE,session,adapt,profile,configure,trace,save_trace,dmd

from readiness_multiplayer import ensure_playable

from b6_reproduce_v5 import all_balls_free,wait_no_saver

from readiness_games import ROOT

MAPPING=owner_view('l5',0x7E5FB,0x7E63C)
def lit(api):
 b=api.memory(0x2e0,96);n=MAPPING[4]-1;return bool(b[n//8]&(1<<(n%8)))
from lab.config import REPO as ROOT
from lab.runtime import owner_view
from types import SimpleNamespace


def run_case(folder,port,spec):
 kids=spec.get("kids",False)
 with session(folder,port,__file__,game='gw_g6',sound_cpu=True) as (api,r):
   adapt(api);profile(api,tournament=False,awards=True)
   configure(api,{0x1BD3:0,0x1BBD:10,0x1B3B:0})
   ensure_playable(api);trace(api,[(0x5AA0,0x3B),(0x6253,0x2A)])
   shots=[]
   for i in range(24):
    all_balls_free(api);api.pulse(4,'800',after=600);all_balls_free(api)
    row=dict(shot=i+1,frame=api.frames_run,special_lit=lit(api),player_ram=api.memory(0x903,54).hex(),state=api.state())
    shots.append(row);print('TUNNEL',i+1,row['special_lit'],row['state']['live'],flush=True)
    if row['special_lit']:break
   assert shots[-1]['special_lit'],'Special not lit within bounded tunnel shots'
   before=api.marker('special-lit-before-outlane');dmd(api,folder,'special-lit')
   selection=save_trace(api,folder,'tunnel-and-award-selection')
   api.call('monitor',cmd='clear');api.call('monitor',cmd='add',type='sol',id=7)
   wait_no_saver(api);all_balls_free(api);api.pulse(4,'A',after=600)
   events=api.call('monitor/log')['actions'];after=api.marker('special-outlane-collected');dmd(api,folder,'special-collected')
   assert not lit(api),'Special indicator remained lit after outlane collection'
   assert any(e['type']=='sol' and e['id']==7 and e['val'] for e in events),'No positive Special award knocker command'
   (folder/'shots.json').write_text(json.dumps(shots,indent=2)+'\n');(folder/'award-events.json').write_text(json.dumps(events,indent=2)+'\n')
   r.update(result='PASS',release_contract='Special qualified by tunnel shots and collected through right outlane',shots=len(shots),before_collection=before,after_collection=after,knocker_activations=sum(e['type']=='sol' and e['id']==7 and bool(e['val']) for e in events),limits=['Special credit setting intentionally enabled as a positive emulation control; replay award disabled','Burn Rubber selection limited to this naturally encountered sequence; multiball percentage zero is an intentional operator setting'])

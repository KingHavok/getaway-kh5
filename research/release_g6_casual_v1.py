"""Port of authored historical controller release_g6_casual_v1. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import json

from release_g6_lab_v2 import BASE,session,adapt,profile,trace,save_trace,dmd

from readiness_multiplayer import ensure_playable

from b6_reproduce_v5 import all_balls_free,wait_no_saver
from lab.config import REPO as ROOT
from lab.runtime import owner_view
from types import SimpleNamespace


def run_case(folder,port,spec):
 kids=spec.get("kids",False)
 with session(folder,port,__file__,game='gw_g6',sound_cpu=True) as (api,r):
    adapt(api);profile(api,kids=kids,tournament=False,awards=True);ensure_playable(api)
    trace(api,[(0x7317,0x36),(0x5D3B,0x2A),(0x6253,0x2A),(0x696B,0x24)])
    before=api.marker('casual-Burn-Rubber-before-tunnel');assert api.memory(0x937,1)==b'\0'
    api.pulse(4,'800',after=600)
    api.wait('natural Burn Rubber award settles',lambda s:api.memory(0x937,1)==b'\x01',limit=2400)
    api.frames(600);all_balls_free(api)
    after=api.marker('casual-Burn-Rubber-after-award');dmd(api,folder,'awarded')
    log=save_trace(api,folder,'native-selection')
    assert any((t['pc'],t['bank'])==(0x7317,0x36) for t in log)
    assert any((t['pc'],t['bank'])==(0x5D3B,0x2A) for t in log)
    assert api.memory(0x1B51,2)==b'\0\0'
    wait_no_saver(api)
    r.update(result='PASS',release_contract='First native non-tournament Burn Rubber award in release profile',kids=kids,before_award=before,after_award=after,native_selected_id=api.memory(0x89d,1)[0],burn_rubber_count=api.memory(0x937,1)[0],limits=['Two deterministic native selections; not statistical coverage of every random award'])
    print(folder.name,'PASS',r['native_selected_id'],flush=True)

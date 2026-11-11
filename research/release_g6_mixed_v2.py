"""Port of authored historical controller release_g6_mixed_v2. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import hashlib

import json

from release_g6_lab_v2 import BASE, session, adapt, profile, configure, trace, save_trace, dmd

from readiness_session import qualify_locks, collect_lock

from readiness_multiplayer import ensure_playable, drain_turn, lights

from readiness_shared_matrix import advance_to

from b6_reproduce_v5 import all_balls_free, wait_no_saver

import remaining_multiball_matrix_v4 as modes

def end_turn(api):
    state=api.state()
    drain_turn(api,state['player'],state['ball'])

def collect_awards(api,folder,stages):
    for award in range(3):
        all_balls_free(api)
        for _ in range(18):
            if api.state()['switches'][54]:break
            api.pulse(4,'5',after=300)
            all_balls_free(api)
        assert api.state()['switches'][54]
        trace(api,[(0x6253,0x2A),(0x66C0,0x2A),(0x66B0,0x2A),(0xF441,0x2A)])
        api.call('debugger/tracepoints',cmd='add',addr='F441')
        api.pulse(4,'6',after=600)
        all_balls_free(api)
        log=save_trace(api,folder,f'award-{award}')
        assert not any(t['pc']==0x6253 for t in log),'Multiball restarted on an award'
        stages.append(api.marker(f'award-{award}'))
        dmd(api,folder,f'award-{award}')

def finish_game(api):
    turns=[]
    for _ in range(50):
        state=api.state()
        if state['phase'][1]:return turns
        ensure_playable(api);wait_no_saver(api)
        state=api.state();identity=(state['player'],state['ball'])
        turns.append(dict(player=identity[0],ball=identity[1],frame=api.frames_run))
        for _ in range(9):
            api.pulse(5,'2000',after=300)
            state=api.state()
            if state['phase'][1] or (state['player'],state['ball'])!=identity:break
        else:raise TimeoutError('Ordinary drain did not end this turn')
    raise TimeoutError('New game did not reach attract')
from lab.config import REPO as ROOT
from lab.runtime import owner_view
from types import SimpleNamespace


def run_case(folder,port,spec):
 a=SimpleNamespace(kids=spec.get("kids",False),port=port)
 players=4 if a.kids else 2
 with session(folder,a.port,__file__,game='gw_g6',sound_cpu=True) as (api,r):
         adapt(api);profile(api,players=players,kids=a.kids,awards=False)
         owners=[1,2] if a.kids else [1];saved={};stages=[]
         for owner in owners:
             advance_to(api,owner,players);ensure_playable(api);qualify_locks(api)
             collect_lock(api,1,player=owner);ensure_playable(api);wait_no_saver(api)
             s=api.state();saved[owner]=dict(credits=s['lock_credits'][owner-1],gear=s['gears'][owner-1])
             stages.append(api.marker(f'owner-{owner}-saved'));end_turn(api)
         recipient=3 if a.kids else 2
         advance_to(api,recipient,players);ensure_playable(api);qualify_locks(api)
         trace(api,[(0x6253,0x2A),(0x6AD4,0x2A)])
         for credit in [1,2,3]:
             collect_lock(api,credit,player=recipient)
             if credit<3:ensure_playable(api)
         api.wait('recipient standard multiball',lambda s:s['live']==3,limit=2400)
         log=save_trace(api,folder,'recipient-start')
         assert sum(t['pc']==0x6253 for t in log)==1
         for owner in owners:assert api.state()['lock_credits'][owner-1]==1
         stages.append(api.marker('recipient-multiball'))
         collect_awards(api,folder,stages)
         wait_no_saver(api);end_turn(api)
         redline_player=4 if a.kids else 1
         advance_to(api,redline_player,players);ensure_playable(api)
         trace(api,[(0x6A88,0x2A),(0x6AD4,0x2A),(0x6253,0x2A)])
         modes.redline(api,redline_player,a.kids)
         log=save_trace(api,folder,'redline-start')
         assert sum(t['pc']==0x6AD4 for t in log)==1
         stages.append(api.marker('redline-active'))
         wait_no_saver(api);modes.tilt(api);end_turn(api)
         if a.kids:
             advance_to(api,1,players)
             s=api.state();assert s['lock_credits'][:2]==[1,1]
             assert [s['gears'][i-1] for i in owners]==[saved[i]['gear'] for i in owners]
             ensure_playable(api)
             for credit in [2,3]:
                 collect_lock(api,credit,player=1)
                 if credit<3:ensure_playable(api)
             api.wait('returning owner multiball',lambda s:s['live']==3,limit=2400)
             stages.append(api.marker('owner-returned-to-legitimate-multiball'))
             wait_no_saver(api);end_turn(api)
             assert api.state()['player']==2 and api.state()['lock_credits'][1]==1
         state=api.state()
         if state['ball']==1:
             ensure_playable(api);end_turn(api)
         ensure_playable(api)
         clean,accepted=modes.restart_and_recover(api,players,False)
         assert not ({0xF2,0xF3,0xB7,0x138,0x139}&set(clean['state']['task_ids']))
         stages.extend([clean,accepted])
         turns=finish_game(api)
         assert len(turns)==players*(5 if a.kids else 3)
         attract=api.marker('completed-new-game-attract-before-physical-return')
         for _ in range(12):
             state=api.state()
             if all(state['switches'][n] for n in [56,57,58]):break
             if any(b['installed'] and b['state']==258 for b in api.io()['balls']):
                 api.pulse(5,'2000',after=300)
             else:api.frames(120)
         final=api.marker('completed-new-game-attract')
         assert final['state']['phase'][1]==1
         assert all(final['state']['switches'][n] for n in [56,57,58])
         (folder/'stages.json').write_text(json.dumps(stages,indent=2)+'\n')
         r.update(result='PASS',release_contract='continuous mixed multiplayer',players=players,kids=a.kids,
             passive_owners=saved,new_game_turns=turns,attract_before_physical_return=attract,final=final,
             helper_sha256=hashlib.sha256(__import__('pathlib').Path(__import__('release_g6_lab_v2').__file__).read_bytes()).hexdigest(),
             limits=['Award traces need final scoring audit before release qualification','Extra balls deliberately disabled in mixed turn-count cases; separate positive award contracts required'])
         print(folder.name,'PASS',flush=True)

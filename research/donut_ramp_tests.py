"""Port of authored historical controller donut_ramp_tests. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import concurrent.futures

import itertools

import json

import pathlib

import traceback

from fault_lab import session,setup,ensure_playable,qualify_locks,collect_lock,wait_saver,drain_turn,installed

from pilot_donut_trap import edge

def down(io):return next(s['physical'] for s in io['switches'] if s['id']==54)

def run_case(folder,port,spec,game):
    with session(folder,port,__file__,game=game) as (api,r):
        setup(api,extended=spec['extended']);ensure_playable(api);qualify_locks(api)
        for credit in range(1,spec['locks']+1):collect_lock(api,credit);ensure_playable(api)
        wait_saver(api)
        api.call('debugger/tracepoints',cmd='clear')
        for addr,bank in [('481A','30'),('4888','30'),('4905','30'),('4C1A','2A'),
                          ('4C82','2A'),('6253','2A'),('6A88','2A')]:
            api.call('debugger/tracepoints',cmd='add',addr=addr,bank=bank)
        before=api.marker('before-right-orbit-entry')
        assert down(before['io'])==1
        edge(api,18);edge(api,17)
        first=api.marker('right-orbit-entry-raised-ramp')
        assert down(first['io'])==0,'Right-orbit entry did not raise the physical-model ramp'
        scenario=spec['scenario'];samples=[];faulted=None;injection=None
        if scenario=='fast':
            edge(api,16);edge(api,15);api.frames(180)
        else:
            # Slow ball has not reached exit 16/15 when the ordinary passage
            # interval expires. Its simulator free-ball slot is unswitched.
            api.frames(180)
            trapped=api.marker('slow-ball-unreported-after-ramp-dropped')
            assert down(trapped['io'])==1,'Did not create the dropped-ramp trap precondition'
            if scenario=='failed-lift':injection=api.fault('mechanism',2,0)
            elif scenario.startswith('feedback-'):injection=api.fault('switch',54,int(scenario[-1]))
            if injection:
                for index in range(30):
                    api.frames(60);samples.append(api.marker(f'faulted-trap-{index}'))
                faulted=api.marker('faulted-trap-before-repair')
                if scenario=='failed-lift':
                    assert down(faulted['io'])==1
                    m=next(m for m in faulted['io']['mechanisms'] if m['id']==2)
                    assert m['changed_observations']>0
                    api.fault('mechanism',2,-1)
                else:
                    old=next(s for s in injection['switches'] if s['id']==54)
                    new=next(s for s in faulted['io']['switches'] if s['id']==54)
                    assert new['changed_reads']>old['changed_reads']
                    api.fault('switch',54,-1)
            stage=int(scenario[-1]) if scenario.startswith('search-') else 1
            for index in range(1200):
                io=api.io()
                traces=api.call('debugger/tracepoints')['log']
                reached=any(t['pc']==0x481A and t['bank']==0x30 and t['a']>=stage for t in traces)
                if down(io)==0 and reached:break
                api.frames(6)
            else:raise TimeoutError('No physical-model lift after trap/search/repair')
            lifted=api.marker('native-search-lift-permits-return')
            edge(api,16);edge(api,15);api.frames(180)
            r.update(trapped=trapped,search_stage_requested=stage,release_lift=lifted)
        returned=api.marker('trapped-ball-returns-to-playfield-switches')
        count_before=sum(t['pc']==0x481A for t in api.call('debugger/tracepoints')['log'])
        for _ in range(6):edge(api,31);api.frames(174)
        found=api.marker('continued-activity-after-return')
        traces=api.call('debugger/tracepoints')['log']
        assert sum(t['pc']==0x481A for t in traces)==count_before,'Search escalated during returned-ball activity'
        assert (found['state']['player'],found['state']['ball'],found['state']['phase'])==(1,1,[0,0,0])
        assert found['state']['lock_credits'][0]==spec['locks']
        assert len(installed(found['io']))==3 and found['state']['live']<=3
        assert not any(t['pc'] in [0x6253,0x6A88] for t in traces),'Trap recovery spuriously started multiball'
        assert all(s['forced']==-1 for s in found['io']['switches'])
        assert all(m['forced_response']==-1 for m in found['io']['mechanisms'])
        drain_turn(api,1,1)
        ensure_playable(api);qualify_locks(api)
        collect_lock(api,spec['locks']+1)
        api.frames(300)
        final=api.marker('next-ball-ramp-and-legitimate-lock')
        assert final['state']['lock_credits'][0]==spec['locks']+1 or final['state']['live']==3
        traces=api.call('debugger/tracepoints')['log'];assert len(traces)<512
        (folder/'traces.json').write_text(json.dumps({'log':traces},indent=2)+'\n')
        r.update(result='PASS',specification=spec,before=before,first_passage_lift=first,
                 injection=injection,faulted=faulted,returned=returned,found=found,final=final,
                 limits=['Entry/exit switch and ramp-model response contract; no under-ramp collision simulation',
                         'Returned switch edges represent release only after an observed model lift',
                         'Digital command timing is measured separately; no release force/current/temperature certification'])
    return r
from lab.config import REPO as ROOT

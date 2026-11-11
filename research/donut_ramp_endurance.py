"""Port of authored historical controller donut_ramp_endurance. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse,json,pathlib,traceback

from fault_lab_candidate import session,setup,ensure_playable,qualify_locks,collect_lock,installed

from readiness_multiplayer import wait_saver,drain_turn

from pilot_donut_trap import edge

from donut_ramp_tests import down

def run(folder,port,scenario,game):
    with session(folder,port,__file__,game=game) as (api,r):
        setup(api,extended=True);ensure_playable(api);qualify_locks(api)
        for credit in [1,2]:collect_lock(api,credit);ensure_playable(api)
        wait_saver(api)
        api.call('debugger/tracepoints',cmd='clear')
        for address,bank in [('481A','30'),('6253','2A'),('6A88','2A')]:
            api.call('debugger/tracepoints',cmd='add',addr=address,bank=bank)
        before=api.marker('before-right-orbit-entry');assert down(before['io'])==1
        edge(api,18);edge(api,17)
        first=api.marker('right-orbit-entry-raised-ramp');assert down(first['io'])==0
        api.frames(180);trapped=api.marker('slow-ball-unreported-after-ramp-dropped');assert down(trapped['io'])==1
        kind,n,value=('mechanism',2,0) if scenario=='failed-lift-long' else ('switch',54,int(scenario[-1]))
        injection=api.fault(kind,n,value)
        for seconds in range(10,601,10):api.frames(600);api.marker(f'trapped-fault-held-{seconds}-seconds')
        faulted=api.marker('faulted-trap-before-repair')
        if kind=='mechanism':
            assert down(faulted['io'])==1
            assert next(x for x in faulted['io']['mechanisms'] if x['id']==n)['changed_observations']>0
        else:
            a=next(x for x in injection['switches'] if x['id']==n);b=next(x for x in faulted['io']['switches'] if x['id']==n)
            assert b['changed_reads']>a['changed_reads'] and b['last_seen']==value
        api.fault(kind,n,-1)
        for _ in range(1200):
            io=api.io()
            if down(io)==0:break
            api.frames(6)
        else:raise TimeoutError('No ramp-model lift within 120 seconds of repair')
        lifted=api.marker('native-search-lift-permits-return');edge(api,16);edge(api,15);api.frames(180)
        returned=api.marker('trapped-ball-returns-to-playfield-switches')
        count=len(api.call('debugger/tracepoints')['log'])
        for _ in range(6):edge(api,31);api.frames(174)
        found=api.marker('continued-activity-after-return')
        traces=api.call('debugger/tracepoints')['log'];assert len(traces)==count and len(traces)<512
        assert (found['state']['player'],found['state']['ball'],found['state']['phase'])==(1,1,[0,0,0])
        assert found['state']['lock_credits'][0]==2 and len(installed(found['io']))==3
        assert not any(t['pc'] in [0x6253,0x6A88] for t in traces)
        search=[t for t in traces if (t['pc'],t['bank'])==(0x481A,0x30)]
        assert len(search)>=20,'Repeated-search endurance precondition was not reached'
        drain_turn(api,1,1);ensure_playable(api);qualify_locks(api);collect_lock(api,3);api.frames(300)
        final=api.marker('next-ball-ramp-and-legitimate-lock');assert final['state']['live']==3
        (folder/'traces.json').write_text(json.dumps(api.call('debugger/tracepoints'),indent=2)+'\n')
        r.update(result='PASS',specification=dict(scenario=scenario,locks=2,extended=True,fault_seconds=600),
                 before=before,first_passage_lift=first,trapped=trapped,injection=injection,faulted=faulted,
                 release_lift=lifted,returned=returned,found=found,final=final,search_attempts_before_return=len(search),
                 limits=['Withheld exit contacts and physical-model ramp position; no collision or release-force simulation',
                         'Ten-minute command endurance only; current, temperature and mechanical wear require hardware measurements'])
from lab.config import REPO as ROOT

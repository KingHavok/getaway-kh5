"""Port of authored historical controller fault_campaign_v3. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import concurrent.futures

import json

import pathlib

from fault_lab import session,setup,configure,installed,observe,ensure_playable,qualify_locks,collect_lock,wait_saver,drain_turn

def free_count(io): return sum(b['state']==258 for b in installed(io))

def start_mb(api):
    ensure_playable(api);qualify_locks(api)
    for credit in range(1,4):
        collect_lock(api,credit)
        if credit<3:ensure_playable(api)
    api.wait('MB initialized',lambda s:s['live']==3,limit=2400)
    api.frames(600)

def run_case(folder,port,spec,game):
    with session(folder,port,__file__,game=game) as (api,record):
        kind,number,value=spec['kind'],spec['id'],spec['value']
        early=spec['phase']=='serve'
        if early:
            api.frames(1200)
            extended=spec.get('extended',False)
            configure(api,{0x1B1F:5 if extended else 3,0x1B21:1,0x1B23:0,0x1B39:3,0x1B43:0,0x1B51:1,
                           0x1B5F:0,0x1B61:0,0x1B9D:1,0x1BBF:0,0x1BC9:0,0x1BCB:99 if extended else 20,
                           0x1BD3:20,0x1BD5:99 if extended else 20})
            injection=api.fault(kind,number,value)
            api.button('200',after=300);api.button('200',after=120)
            # A failed trough sensor may legitimately refuse a start. Preserve
            # that observation instead of assuming a two-player game began.
        else:
            setup(api,players=2,extended=spec.get('extended',False))
        if not early:
            if spec['phase']!='plunger':ensure_playable(api)
            if spec['phase'] in ['lock','mb','ramp-up']:
                qualify_locks(api)
            if spec['phase']=='ramp-up':
                api.wait('ramp lowered',lambda s:s['switches'][54]==1)
            if spec['phase'] in ['mb','diverter']:
                start_mb(api)
            injection=api.fault(kind,number,value)
        before=api.marker('fault-before-stimulus')
        if spec['phase'] in ['lock','ramp-down']:
            if spec['phase']=='ramp-down':qualify_locks(api)
            api.pulse(4,'6',after=600)
        elif spec['phase']=='ramp-up':
            for credit in range(1,4):
                collect_lock(api,credit)
                if credit<3:ensure_playable(api)
            api.frames(600)
        elif spec['phase']=='locker':
            # Place all three balls in the lock while the eject response fails.
            ensure_playable(api);qualify_locks(api)
            for credit in range(1,4):
                if credit<3:
                    collect_lock(api,credit);ensure_playable(api)
                else:
                    api.wait('ramp down for third physical ball',lambda s:s['switches'][54]==1)
                    api.pulse(4,'6',after=600)
                    io=api.io()
                    assert sum(api.state()['switches'][n] for n in [74,75,76])==3
            api.frames(600)
        elif spec['phase']=='tunnel':api.pulse(4,'800',after=600)
        elif spec['phase']=='drain':
            wait_saver(api);api.pulse(5,'2000',after=600)
        elif spec['phase']=='plunger':api.pulse(1,'8000',on=12,after=600)
        elif spec['phase']=='diverter':api.pulse(4,'5',after=600)
        elif spec['phase']=='serve':api.pulse(1,'8000',on=12,after=600)
        observed=observe(api,spec.get('seconds',30),activity=spec.get('activity',False))
        faulted=api.marker('fault-end')
        api.fault(kind,number,-1)
        api.frames(120)
        # Recovery stimulus is cabinet/playfield input only. Never teleport a
        # ball, edit game RAM, reset, or substitute a successful device response.
        if spec['phase'] in ['serve','plunger']:
            api.pulse(1,'8000',on=12,after=300)
        recovering=[]
        for index in range(120):
            snap=api.marker(f'recovery-{index}')
            recovering.append(snap)
            if free_count(snap['io'])>0 or snap['state']['switches'][78] or snap['state']['phase'][1]:
                break
            api.frames(60)
        final=api.marker('recovery-end')
        assert len(installed(final['io']))==3
        assert all(s['state']['live']<=3 for s in observed+recovering), 'ROM ball accounting exceeds three installed balls'
        assert not any(x['forced']>=0 for x in final['io']['switches'])
        assert not any(x['forced_response']>=0 for x in final['io']['mechanisms'])
        if kind=='switch':
            stats=next(x for x in faulted['io']['switches'] if x['id']==number)
            exercised=stats['changed_reads']>next(x for x in injection['switches'] if x['id']==number)['changed_reads']
        else:
            stats=next((x for x in faulted['io']['mechanisms'] if x['id']==number),{})
            exercised=stats.get('changed_observations',0)>0
        recovered=bool(free_count(final['io']) or final['state']['switches'][78] or final['state']['phase'][1])
        assert recovered, 'No playable ball or attract state within two minutes after restoring device'
        # Do not stop at "a free ball exists": advance naturally, then prove
        # that another turn can lower the ramp and accept a legitimate lock.
        if final['state']['phase'][1]:
            api.button('200',after=300)
        elif (final['state']['player'],final['state']['ball']) == (before['state']['player'],before['state']['ball']):
            if final['state']['live']<=1:ensure_playable(api)
            now=api.state()
            drain_turn(api,now['player'],now['ball'])
        ensure_playable(api)
        qualify_locks(api)
        state=api.state()
        expected=state['lock_credits'][state['player']-1]+1
        assert 1<=expected<=3, 'Invalid retained lock-credit count'
        collect_lock(api,expected,player=state['player'])
        api.frames(300)
        repaired_lock=api.marker('post-repair-next-turn-lock')
        assert any(repaired_lock['state']['switches'][n] for n in [74,75,76]) or repaired_lock['state']['live']==3
        traces=api.call('debugger/tracepoints')
        (folder/'traces.json').write_text(json.dumps(traces,indent=2)+'\n')
        record.update(result='PASS',kind='fault characterization; qualified only for explicit invariants',
                      specification=spec,fault_exercised=exercised,recovered_to_playable_or_attract=recovered,
                      injection=injection,before=before,faulted=faulted,final=final,
                      post_repair_lock=repaired_lock,post_repair_lock_ok=True,
                      qualification='OBSERVED; interpret recovery and coil findings before release',
                      limits=['Physical movement follows the native PinMAME model; accelerator velocity/current are not modeled',
                              'A sensor fault may legitimately change scoring/lock credit; no unwitnessed progress preservation is assumed',
                              'PASS here asserts trace/inventory/task/accounting contracts, not complete fault tolerance'])
    return record

def specs():
    work=[]
    for id,phase in [(11,'serve'),(12,'plunger'),(16,'drain'),(9,'tunnel'),(3,'ramp-down'),(2,'ramp-up'),(4,'locker'),(10,'diverter')]:
        work.append(dict(kind='mechanism',id=id,value=0,phase=phase,seconds=30))
    work.append(dict(kind='mechanism',id=10,value=1,phase='diverter',seconds=30))
    for id,phase in [(54,'ramp-down'),(55,'drain'),(56,'serve'),(57,'serve'),(58,'serve'),
                     (74,'lock'),(75,'lock'),(76,'lock'),(78,'serve'),
                     (81,'diverter'),(82,'diverter'),(83,'diverter'),(84,'diverter'),(85,'diverter')]:
        for value in [0,1]:work.append(dict(kind='switch',id=id,value=value,phase=phase,seconds=30))
    return work
from lab.config import REPO as ROOT

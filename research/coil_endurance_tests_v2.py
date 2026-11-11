"""Port of authored historical controller coil_endurance_tests_v2. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse,concurrent.futures,itertools,json,pathlib,traceback

from fault_lab_candidate import session,setup,ensure_playable,installed

from flipper_fault_tests_v2 import FLIPPERS

def edge(api,number,on=6,after=54):
    api.call('input',sw=number,val=1);api.frames(on)
    api.call('input',sw=number,val=0)
    if after:api.frames(after)

def run_case(folder,port,spec,game):
    with session(folder,port,__file__,game=game) as (api,r):
        setup(api);ensure_playable(api)
        for addr,bank in [('5F96','39'),('5FCB','39'),('8E79',None)]:
            params=dict(cmd='add',addr=addr)
            if bank:params['bank']=bank
            api.call('debugger/tracepoints',**params)
        if spec['kind']=='flipper':
            f=spec['flipper'];injected=api.fault('switch',f['eos'],spec['forced'])
            before=api.marker('before-long-hold')
            api.call('input/port',port=1,val=f['input'])
            samples=[]
            for n in range(30):
                if n%4==0:edge(api,31)
                else:api.frames(60)
                snap=api.marker(f'held-{n+1}-seconds');samples.append(snap)
                if n>=1:assert not((~snap['io']['raw_registers'][4])&(1<<f['stroke']))
            held=api.marker('after-thirty-second-hold')
            assert held['state']['phase']==[0,0,0] and held['state']['live']==1
            assert (~held['io']['raw_registers'][4])&(1<<f['hold']),'Own hold winding was never enabled'
            rows=[json.loads(line) for line in (folder/'raw-coils.jsonl').open()]
            strobes=[w for w in rows if w['kind']=='write' and w['address']==0x3FD4
                     and before['io']['time']<=w['time']<=held['io']['time']]
            if spec['forced']<1:
                assert any((~w['value'])&(1<<f['stroke']) for w in strobes),'No positive initial stroke'
            assert not any((~w['value'])&sum(1<<i for i in [0,2,4] if i!=f['stroke']) for w in strobes),'Another installed flipper stroke fired'
            if spec['shutdown']=='tilt':
                for _ in range(4):
                    if api.state()['phase'][0]:break
                    api.button('400',on=12,after=60)
                assert api.state()['phase'][0]==1
            else:api.button('800',on=12,after=60)
            api.frames(60);stopped=api.marker('shutdown-with-button-still-held')
            if spec['shutdown']=='slam':
                traces=api.call('debugger/tracepoints')['log']
                assert sum((t['pc'],t['bank'])==(0x5F96,0x39) for t in traces)==1,'Native Slam Tilt handler did not execute'
                assert any((t['pc'],t['bank'])==(0x5FCB,0x39) for t in traces),'Native Slam Tilt abort branch not reached'
                assert any(t['pc']==0x8E79 for t in traces),'Native Slam Tilt soft restart was not reached'
                (folder/'shutdown-traces.json').write_text(json.dumps({'log':traces},indent=2)+'\n')
            assert ((~stopped['io']['raw_registers'][4])&63)==0,'Installed flipper windings remain commanded after shutdown'
            api.call('input/port',port=1,val='0');api.frames(60)
            api.fault('switch',f['eos'],-1)
            if spec['forced']>=0:
                a=next(s for s in injected['switches'] if s['id']==f['eos'])
                b=next(s for s in held['io']['switches'] if s['id']==f['eos'])
                assert b['changed_reads']>a['changed_reads'] and b['last_seen']==spec['forced']
            r.update(before=before,held=held,stopped=stopped)
        else:
            number=spec['switch'];injected=api.fault('switch',number,spec['forced'])
            before=api.marker('before-stuck-firing-switch')
            for n in range(30):
                if n%4==0:
                    edge(api,number,on=6,after=0)
                    edge(api,62 if number!=62 else 63,on=6,after=48)
                else:api.frames(60)
            faulted=api.marker('after-thirty-second-stuck-switch')
            a=next(s for s in injected['switches'] if s['id']==number)
            b=next(s for s in faulted['io']['switches'] if s['id']==number)
            assert b['changed_reads']>a['changed_reads'] and b['last_seen']==spec['forced']
            api.fault('switch',number,-1);api.frames(60)
            if number==25:
                for n in [44,45,46]:edge(api,n)
                api.frames(120)
            repaired=api.marker('before-repaired-positive-hit')
            edge(api,number,on=12,after=120)
            positive=api.marker('after-repaired-positive-hit')
            api.io()  # flush paused raw trace before inspecting complete writes
            rows=[json.loads(line) for line in (folder/'raw-coils.jsonl').open()]
            out=spec['output'];address=0x3FE1 if out<=8 else 0x3FE3;mask=1<<((out-1)%8)
            assert any(w['kind']=='write' and w['address']==address and w['value']&mask
                       and repaired['io']['time']<=w['time']<=positive['io']['time'] for w in rows),'No repaired-switch positive coil response'
            r.update(before=before,faulted=faulted,repaired=repaired,positive=positive)
        final=api.marker('fault-restored-at-end')
        assert len(installed(final['io']))==3
        assert all(s['forced']==-1 for s in final['io']['switches'])
        r.update(result='PASS',specification=spec,final=final,
                 limits=['Command duration and shutdown only; no physical current or temperature measurement',
                         'Only listed switches, thirty-second holds and the specified tilt/slam endings',
                         'Hold-winding current and high-power stroke duration are separate quantities'])
    return r

def design():
    flippers=[(dict(kind='flipper',flipper=f,forced=v,shutdown=s),g) for f,v,s,g in itertools.product(FLIPPERS,[-1,0,1],['tilt','slam'],['gw_g6','gw_l5'])]
    switches=[(dict(kind='firing-switch',switch=n,output=o,forced=v),g) for (n,o),v,g in itertools.product([(25,8),(31,5),(32,6),(61,13),(62,14),(63,15)],[0,1],['gw_g6','gw_l5'])]
    return flippers+switches
from lab.config import REPO as ROOT

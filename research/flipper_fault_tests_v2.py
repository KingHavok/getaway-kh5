"""Port of authored historical controller flipper_fault_tests_v2. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import concurrent.futures

import json

import pathlib

from fault_lab_flippers import session,setup,ensure_playable,installed

FLIPPERS=[dict(name='lower-right',input='2',eos=111,stroke=0,hold=1),
          dict(name='lower-left',input='1',eos=113,stroke=2,hold=3),
          dict(name='upper-right',input='8',eos=115,stroke=4,hold=5)]

def run_case(folder,port,game,flipper,forced):
    with session(folder,port,__file__,game=game) as (api,result):
        setup(api);ensure_playable(api)
        injected=api.fault('switch',flipper['eos'],forced)
        before=api.marker('before-flipper-hold')
        api.call('input/port',port=1,val=flipper['input'])
        api.frames(120)
        held=api.marker('held-two-seconds')
        mask=1<<flipper['stroke']
        assert not ((~held['io']['raw_registers'][4])&mask), 'Stroke winding still commanded after two-second hold'
        tilt_attempts=0
        while api.state()['phase'][0]!=1 and tilt_attempts<4:
            api.button('400',on=12,after=60);tilt_attempts+=1
        assert api.state()['phase'][0]==1,'Tilt stimulus not accepted'
        api.frames(60)
        tilted=api.marker('tilted-while-button-held')
        assert ((~tilted['io']['raw_registers'][4])&0x3F)==0,'Installed flipper winding remains commanded after tilt'
        api.call('input/port',port=1,val='0');api.frames(60)
        api.fault('switch',flipper['eos'],-1)
        final=api.marker('released-and-restored')
        assert len(installed(final['io']))==3
        observed=set()
        with (folder/'raw-coils.jsonl').open() as stream:
            for line in stream:
                r=json.loads(line)
                if r['kind']=='write' and r['address']==0x3FD4 and before['io']['time']<=r['time']<=held['io']['time']:
                    for bit in [0,2,4]:
                        if (~r['value'])&(1<<bit):observed.add(bit)
        assert observed <= {flipper['stroke']},('Other installed flipper stroke activated',observed)
        if forced<1:assert observed=={flipper['stroke']},'No stroke observed under neutral/open EOS'
        sensor=next(x for x in held['io']['switches'] if x['id']==flipper['eos'])
        base=next(x for x in injected['switches'] if x['id']==flipper['eos'])
        result.update(result='PASS',flipper=flipper,eos_forced=forced,
                      fault_exercised=forced>=0 and sensor['changed_reads']>base['changed_reads'],
                      stroke_channels_observed=sorted(observed),before=before,held=held,tilted=tilted,final=final,
                      limits=['Digital stroke timeout and tilt shutdown; not current/temperature or physical force',
                              'Two-second hold only; longer held-button endurance remains a separate test'])
    return result
from lab.config import REPO as ROOT

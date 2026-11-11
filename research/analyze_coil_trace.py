"""Port of authored historical controller analyze_coil_trace. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
import argparse

import bisect

import json

import pathlib

import gzip

import hashlib

ANALYZER_SHA256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()

NAMES={1:'Diverter high',2:'Up ramp',3:'Down ramp',4:'Locker',5:'Left slingshot',6:'Right slingshot',
       7:'Knocker',8:'Kickback',9:'Tunnel eject',10:'Diverter low/hold',11:'Trough release',
       12:'Plunger',13:'Top jet',14:'Left jet',15:'Bottom jet',16:'Outhole',
       17:'Right bank flasher',18:'Supercharger flasher',19:'Left sling flasher',20:'Free Ride flasher',
       21:'Left ramp flasher',22:'Left bank flasher',23:'Flipper flasher',24:'Right sling flasher',25:'Supercharger enable 1',
       26:'Supercharger enable 2',27:'Revolving lamp',28:'Supercharger enable 3'}

FLIP=['LR stroke','LR hold','LL stroke','LL hold','UR stroke','UR hold','UL unused stroke','UL unused hold']

ADDRESSES={0x3FE1:range(1,9),0x3FE3:range(9,17),0x3FE2:range(17,25),0x3FE0:range(25,33),
           0x3FD4:[f'F{i}' for i in range(8)]}

def maximum_on(intervals,window,start,end):
    if end-start<window:return None
    starts=[a for a,b in intervals];prefix=[0.0]
    for a,b in intervals:prefix.append(prefix[-1]+b-a)
    def integral(t):
        i=bisect.bisect_right(starts,t)-1
        return 0.0 if i<0 else prefix[i]+max(0,min(t,intervals[i][1])-intervals[i][0])
    candidates={start+window,end}
    for a,b in intervals:
        for point in [a,b,a+window,b+window]:
            if start+window<=point<=end:candidates.add(point)
    return max(integral(t)-integral(t-window) for t in candidates)/window

def analyze(folder):
    folder=pathlib.Path(folder);result=json.loads((folder/'result.json').read_text())
    end=result['final_io']['time'];start=0.0
    active={};intervals={};counts={};first={};last={};registers={address:255 if address==0x3FD4 else 0 for address in ADDRESSES}
    overlap_start=None;overlaps=[];writes=0;previous=-1;faults=[]
    raw=folder/'raw-coils.jsonl'
    stream_source=raw.open() if raw.exists() else gzip.open(str(raw)+'.gz','rt')
    with stream_source as stream:
        for line in stream:
            row=json.loads(line)
            if row['kind']!='write':
                if row['kind'] in ['fault','clear_faults']:faults.append(row)
                continue
            writes+=1;assert row['seq']==writes
            t=row['time'];assert t>=previous-1e-9;previous=t
            address,value=row['address'],row['value'];assert address in ADDRESSES
            old=registers[address];registers[address]=value
            inverse=255 if address==0x3FD4 else 0
            for bit,coil in enumerate(ADDRESSES[address]):
                before=bool((old^inverse)&(1<<bit));after=bool((value^inverse)&(1<<bit))
                if before==after:continue
                first.setdefault(coil,t);last[coil]=t
                if after:
                    active[coil]=t;counts[coil]=counts.get(coil,0)+1
                else:
                    assert coil in active
                    intervals.setdefault(coil,[]).append((active.pop(coil),t))
            both=bool(registers[0x3FE1]&2 and registers[0x3FE1]&4)
            if both and overlap_start is None:overlap_start=t
            if not both and overlap_start is not None:
                overlaps.append((overlap_start,t));overlap_start=None
    assert writes==result['final_io']['write_count']
    assert previous<=end+1e-5
    censored=list(active)
    for coil,t in active.items():intervals.setdefault(coil,[]).append((t,end))
    if overlap_start is not None:overlaps.append((overlap_start,end))
    metrics={}
    fault_on=[f['time'] for f in faults if f['kind']=='fault' and f['value']>=0]
    fault_off=[f['time'] for f in faults if f['kind']=='fault' and f['value']==-1]
    fault_window=(min(fault_on),max(fault_off)) if fault_on and fault_off else None
    for coil in list(range(1,33))+[f'F{i}' for i in range(8)]:
        values=intervals.get(coil,[]);durations=[b-a for a,b in values]
        category=('flipper stroke' if int(coil[1:])%2==0 else 'flipper hold') if isinstance(coil,str) else (
            'diverter hold' if coil==10 else 'flasher' if 17<=coil<=24 else
            'Supercharger enable' if coil in [25,26,28] else 'lamp/GPIO' if coil>=27 else 'pulse coil')
        metrics[str(coil)]={'name':FLIP[int(coil[1:])] if isinstance(coil,str) else NAMES.get(coil,f'Output {coil}'),
                           'category':category,'activations':counts.get(coil,0),
                           'longest_on_seconds':max(durations,default=0),'total_on_seconds':sum(durations),
                           'overall_command_duty':sum(durations)/(end-start) if end>start else 0,
                           'max_sliding_duty':{str(w):maximum_on(values,w,start,end) for w in [1,10,60]},
                           'right_censored':coil in censored}
        if fault_window:
            a,b=fault_window
            clipped=[(max(x,a),min(y,b)) for x,y in values if y>a and x<b]
            metrics[str(coil)]['fault_window']={'start':a,'end':b,
                'command_duty':sum(y-x for x,y in clipped)/(b-a),
                'max_sliding_duty':{str(w):maximum_on(clipped,w,a,b) for w in [1,10,60]}}
    return {'result':'MEASURED; not a thermal safety certificate','folder':str(folder),
            'analyzer_sha256':ANALYZER_SHA256,
            'image_sha1':result['image_sha1'],'emulator_sha256':result['emulator_sha256'],
            'clock':'MAME timer_get_time, seconds; 2MHz main CPU, instruction-level sampling',
            'writes_verified':writes,'duration_seconds':end-start,'coils':metrics,
            'ramp_opposing_command_overlaps':{'count':len(overlaps),'maximum_seconds':max((b-a for a,b in overlaps),default=0),
                                               'total_seconds':sum(b-a for a,b in overlaps)},
            'fault_intervals':faults,
            'limits':['Raw output latch commands; not smoothed monitor states or measured current',
                      'Identical writes retained and verified but do not introduce a new latch edge',
                      'Hold windings, flashers, lamp and accelerator enable outputs have different meanings',
                      'Opposing ramp overlaps are observations for review, not automatically classified unsafe',
                      'No hardware thermal limits are inferred from these measurements']}
from lab.config import REPO as ROOT

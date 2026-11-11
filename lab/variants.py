"""128 deterministic stimulus variants with published scalar/semantic contracts."""
import copy,json,random,hashlib
from pathlib import Path
from . import runtime
from .config import REPO
from .replay import actions
IMPORTANT={0x6091,0x6098,0x6253,0x537A,0x5200,0x45A4,0x56CB,0x56F3,0x5730,0x5776,0x4654}
SCALARS={'008C':[0,1,2],'040F':[0,1],'0928':[0,4],'092C':[0],'0806':[0],'0800':[5,6],
 '0903':[p*54+f for p in range(4) for f in [37,41]],'08E0':list(range(8))}

def template(name):return json.loads((REPO/'research/inputs'/(name+'.json')).read_text())
def req(path,**params):return dict(path='/api/'+path,params=params)
def pulse(port,value,on=6,off=240):return [req('input/port',port=port,val=value),dict(frames=on),req('input/port',port=port,val='0')]+([dict(frames=off)] if off else [])
def snapshot():return [req('info'),req('switches'),req('solenoids'),req('debugger/memory',addr='0000',size=2048),req('debugger/memory',addr='0800',size=512),req('debugger/instrument')]

def design(target):
 rows=[];entries=json.loads((REPO/'research/variant-inputs.json').read_text())['templates']
 def add(name,spec):rows.append(dict(id=name,group='variant',image=target,specification=spec))
 for item in entries:
  if item['name'] not in ['drain_template','locked_template']:add('synthetic-'+item['name'],dict(kind='reference',template=item['name']))
 for locks in [0,2]:
  for delay in [0,1,6,30,60,90,120,132,144,150,155,156,157,180,204,240]:add(f'a9-locks{locks}-delay{delay:03d}',dict(kind='a9_boundary',locks=locks,delay=delay))
 for pulls in range(2,9):
  for gap in [2,4,6]:add(f'shifter-pulls{pulls}-gap{gap}',dict(kind='secret_burst',pulls=pulls,gap=gap))
 for delay in range(0,241,10):add(f'b3-spacing{delay:03d}',dict(kind='b3_overlap',delay=delay))
 for index in range(16):add(f'a1-seed{20261108+index}',dict(kind='a1_jitter',seed=20261108+index))
 if len(rows)!=128:raise AssertionError('Synthetic design coverage changed')
 return rows

def generate(spec):
 kind=spec['kind']
 if kind=='reference':data=template(spec['template'])
 elif kind=='a9_boundary':
  data=template('drain_template');assert data[269]==dict(frames=120)
  data[269:270]=[dict(frames=spec['delay'])] if spec['delay'] else []
  if spec['locks']:data=template('locked_template')[:376]+data[266:]
 elif kind=='secret_burst':
  data=template('secret_timeout_two_launched');assert data[167]['params']['val']==data[176]['params']['val']=='400'
  burst=sum((pulse(4,'400',6,spec['gap']) for _ in range(spec['pulls'])),[]);data=data[:167]+burst+data[185:]
 elif kind=='b3_overlap':
  data=template('core_b3_intro_overlap');assert data[347]==dict(frames=120)
  data[347:348]=[dict(frames=spec['delay'])] if spec['delay'] else []
 elif kind=='a1_jitter':
  data=template('core_a1_cold');rng=random.Random(spec['seed'])
  for i,a in enumerate(data[:-1]):
   direct=a.get('path')=='/api/input' and a.get('params',{}).get('val')==1
   shot=a.get('path')=='/api/input/port' and a.get('params',{}).get('port')==4 and a.get('params',{}).get('val') in ['5','6','12']
   if (direct or shot) and data[i+1]==dict(frames=6):data[i+1]['frames']=rng.randint(4,10)
   if direct and i+3<len(data) and data[i+3]==dict(frames=24):data[i+3]['frames']=rng.randint(18,36)
 else:raise ValueError(kind)
 if kind!='reference':data=[a for a in data if not a.get('path','').startswith('/api/debugger/dmdrec')]
 original_count=len(data);return data+snapshot(),original_count

def traffic(values):
 mapping=runtime.owner_view('l5',0x7E5FB,0x7E63C)
 return [(values[(mapping[n]-1)//8]>>((mapping[n]-1)%8))&1 for n in range(0x16,0x1F)]

def observation(action,data):
 if action.get('path')=='/api/debugger/instrument' and not action.get('params'):
  return dict(kind='native_counts',counts={f'{p["bank"]:02X}:{p["addr"]:04X}':p['count'] for p in data['points'] if p['addr'] in IMPORTANT})
 if action.get('path')=='/api/debugger/memory':
  address=action['params']['addr'].upper()
  if address in SCALARS:return dict(kind='scalar',address=address,values={str(i):data['data'][i] for i in SCALARS[address] if i<len(data['data'])})
  if address=='02E0':return dict(kind='traffic',values=traffic(data['data']))
 return None

def check(spec,events,seen,original_count,saved):
 def values(address):return [e['response']['data'] for e in events if e['action'].get('path')=='/api/debugger/memory' and e['action']['params']['addr']==address]
 high=values('0800')[-1];low=values('0000')[-1]
 counts=[e['response']['points'] for e in events if e['action'].get('path')=='/api/debugger/instrument' and not e['action'].get('params')][-1]
 pc={(p['addr'],p['bank']):p['count'] for p in counts};at=lambda addr,bank=0x2A:pc.get((addr,bank),0)
 details=[]
 if spec['kind']=='reference':
  expected=json.loads((REPO/'research/variant-oracles.json').read_text())[spec['template']]
  actual=[x for e in events if e['index']<original_count and (x:=observation(e['action'],e['response'])) is not None]
  if len(actual)!=len(expected):raise AssertionError('Historical scalar checkpoint count differs')
  for before,after in zip(expected,actual):
   if before['kind']=='native_counts':
    for key,value in before['counts'].items():
     if key.endswith(':6091') and after['counts'].get(key)!=value:details.append(dict(kind='arrival-count-observation',expected=value,actual=after['counts'].get(key)))
     elif after['counts'].get(key)!=value:raise AssertionError(('Native callback count',key,value,after['counts'].get(key)))
   elif before!=after:
    if spec['template']=='core_a2_burn_rubber_probe' and before.get('address')=='0800':
     b=copy.deepcopy(before);a=copy.deepcopy(after);b['values'].pop('5',None);a['values'].pop('5',None)
     if a!=b:raise AssertionError('Burn Rubber stable scalar differs')
     details.append(dict(kind='setup-qualification-observation'))
    else:raise AssertionError(('Historical scalar/traffic checkpoint differs',before,after))
  if spec['template']=='core_a1_cold':
   from .visual import red_light
   details.append(red_light(saved))
 elif spec['kind']=='a1_jitter':
  assert at(0x6091)>=6 and [at(0x6098),at(0x6253),at(0x537A,0x2B)]==[3,1,1] and high[6]==3
 elif spec['kind']=='b3_overlap':
  assert at(0x6253)==0 and at(0x537A,0x2B)==1 and (high[0x128],high[0x12C],high[6])==(2,5,3)
 elif spec['kind']=='secret_burst':
  if at(0x56CB):assert all(at(p)==1 for p in [0x56CB,0x56F3,0x5730,0x5776,0x4654])
  else:
   assert spec['gap']==2 and 1<=at(0x57A1)<=spec['pulls'] and at(0x57D7)==0
   assert all(at(p)==0 for p in [0x56F3,0x5730,0x5776,0x4654])
  assert at(0x6253)==0 and traffic(values('02E0')[-1])==[1]*9 and values('08E0')[-1][1]==0
 elif spec['kind']=='a9_boundary':
  assert low[0x8C:0x8F]==[0,0,0] and low[0x40F]==1 and high[0x12C]==5
  logs=[e['response']['log'] for e in events if e['action'].get('path')=='/api/debugger/tracepoints' and 'save' in e['action']]
  assert logs and len(logs[-1])<512
  initialized=[p for p in logs[-1] if (p['pc'],p['bank'])==(0x6AD4,0x2A)]
  if initialized:
   assert len(initialized)==1;ram=bytes.fromhex(initialized[0]['ram'])
   starts=[p for p in logs[-1] if (p['pc'],p['bank'])==(0x6A88,0x2A)]
   assert len(starts)==1 and ram[0x8C:0x8F]==b'\0\0\0' and ram[0x806]==1
   assert ram[0x40F:0x411]==bytes.fromhex(starts[0]['ram'])[0x40F:0x411]
   assert low[0x410]==ram[0x410] and high[6]==3
  else:assert (low[0x410],high[6])==(2,1)
 return dict(contract=spec['kind'],observations=details,final_live=high[6],native_counts={f'{b:02X}:{p:04X}':n for (p,b),n in pc.items() if p in IMPORTANT})

def run(case,folder,port):
 data,count=generate(case['specification']);script=folder.parent/(case['id']+'.inputs.json');script.write_text(json.dumps(data,indent=2)+'\n')
 events=[]
 with runtime.session(folder,port,__file__) as (api,record):
  seen,diffs,assertions,saved=actions(api,script,folder,observer=observation,events=events)
  contract=check(case['specification'],events,seen,count,saved)
  record.update(result='PASS',variant_contract=contract,script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),assertion_count=assertions)

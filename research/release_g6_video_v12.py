"""Port of authored historical controller release_g6_video_v12. See research/provenance.json.
Run through tools/lab.py; inputs and raw outputs stay in the private workspace.
"""
from lab.runtime import owner_view
import json

from pathlib import Path

ROM=owner_view('l5',0x10000,0x14000)
def word(addr):return int.from_bytes(ROM[addr-0x4000:addr-0x3ffe],'big')

def dx(kind,state):
 p=word(0x7192+2*(kind-0x0f))+4*(state-1)+2
 return int.from_bytes(ROM[p-0x4000:p-0x3ffe],'big',signed=True)

def future(o):
 return int.from_bytes(o[2:4],'big',signed=True)-dx(o[1],max(1,o[0]))+dx(o[1],17) if o[0]<17 else int.from_bytes(o[2:4],'big',signed=True)

from release_g6_lab_v2 import BASE,session,adapt,profile,configure,trace,save_trace,dmd

from readiness_multiplayer import ensure_playable
from lab.config import REPO as ROOT
from lab.runtime import owner_view
from types import SimpleNamespace


def run_case(folder,port,spec):
 kids=spec.get("kids",False)
 with session(folder,port,__file__,game='gw_g6',sound_cpu=True) as (api,r):
   adapt(api);profile(api,awards=True);configure(api,{0x1B25:0,0x1BCF:6});ensure_playable(api)
   trace(api,[(0x696B,0x24),(0x6AB8,0x24),(0x6AD4,0x24),(0x6ADF,0x24),(0x6AEA,0x24),(0x6AF1,0x24),(0x6AF7,0x24),(0x70D9,0x24),(0x70EA,0x24),(0x6B7F,0x24)])
   api.call('debugger/tracepoints',cmd='add',addr='B4C4')
   for _ in range(20):
    s=api.state();gear=s['gears'][0];rpm=api.memory(0x92B,1)[0]
    if gear==3 and rpm==120:break
    if gear<3:api.pulse(4,'400',on=12,after=180)
    api.frames(420);api.pulse(4,'12',after=180)
    print('QUALIFY',gear,rpm,'EB',api.memory(0x411,2).hex(),flush=True)
   assert gear==3 and rpm==120
   api.pulse(4,'800',after=240);samples=[];started=False
   for i in range(900):
    ram=api.memory(0x738,0x190);car=ram[0x2c:0x42];extra=ram[0x170:0x174]
    objects=[ram[0x42+j*22:0x58+j*22] for j in range(5)]
    row=dict(frame=api.frames_run,car=car.hex(),objects=[o.hex() for o in objects],video=api.memory(0x870,0x40).hex())
    samples.append(row)
    if car[14:17]==bytes.fromhex('6cb224'):started=True
    if started and (extra[0] or extra[3] or not car[0]):break
    x=int.from_bytes(car[2:4],'big',signed=True)
    threats=[o for o in objects if o[0]>=1 and o[1] not in [0x12,0x13,0x17,0x18] and o[0]<30 and not (o[2:4]==b'\x00\x14' and o[5:7]==b'\x00\x10')]
    bonuses=[o for o in objects if o[0] and o[1] in [0x12,0x13,0x17,0x18]]
    def cost(target):
     value=abs(target-20)*.02
     for o in threats:
      ox=future(o)
      if ox-44<target<ox+24:
       weight=(1e12 if o[0]>=17 else 1e8 if o[0]==16 else 1e7 if o[0]==15 else 0) if bonuses else (1e9 if o[0]>=17 else o[0]**4)
       value+=weight*(1+min(target-(ox-44),(ox+24)-target)/20)
     for o in bonuses:
      ox=future(o);value+=abs(target-(ox-5))*1e6
     return value
    target=min([v for v in [-2+6*j for j in range(18)] if abs(v-x)<=6],key=cost)
    control=('1' if not started else '1' if target<x-1 else '2' if target>x+1 else '0')
    api.call('input/port',port=1,val=control);api.frames(1)
    if i%60==0:print('VIDEO',i,'car',x,'target',target,'countdown',api.memory(0x8a9,1).hex(),flush=True)
   api.call('input/port',port=1,val='0');dmd(api,folder,'end-steering')
   api.frames(600);log=save_trace(api,folder,'native-video')
   (folder/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')
   print('TRACE',[(hex(t['pc']),t.get('a'),t.get('cc')) for t in log],flush=True)
   assert any(t['pc']==0x70D9 and t['bank']==0x24 for t in log),'Video extra-ball collision not reached'
   assert any(t['pc']==0xB4C4 for t in log),'Native extra-ball award not reached'
   assert api.memory(0x411,2)==b'\x01\x01','Extra ball not actually credited'
   from b6_reproduce_v5 import all_balls_free
   all_balls_free(api)
   r.update(result='PASS',release_contract='Native video gameplay and video extra-ball collision, award and return to play',samples=len(samples),credited_extra_balls=api.memory(0x411,2).hex(),final=api.marker('video-return'))

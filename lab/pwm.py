"""8192 native CPU vectors for the authored atomic PWM stop hook. NEVER BURN fixtures."""
import json,hashlib
from pathlib import Path
from . import runtime
from .config import sha
from replay import emulator,API
def fixture(image):
    code=bytearray();labels={};fixups=[];origin=0xFB40
    def emit(s):code.extend(bytes.fromhex(s))
    def label(s):labels[s]=origin+len(code)
    def ref(op,name):
        emit(op);fixups.append((len(code),name,False));code.extend(b'\0\0')
    def bne(name):
        emit('1026');fixups.append((len(code),name,True));code.extend(b'\0\0')
    emit('1A50 10CE0FF0 862A B73FFC CC0000 FD020A 7F020C')
    ref('8E','timers')
    label('timer');ref('108E','ccs')
    label('cc');emit('7F0200')
    label('shadow')
    emit('B60200 977C B73FE1 EC84 DDE6 A6A4 B70202 1F8A BD7040')
    emit('3401 FD0204 3502 B70206')
    emit('B60200 84FE 917C');bne('fail')
    emit('FC0204');bne('fail')
    emit('DCE6');bne('fail')
    emit('B60202 84F1 8A04 B10206');bne('fail')
    emit('FC020A C30001 FD020A 7C0200');bne('shadow')
    emit('3121');ref('108C','ccend');bne('cc')
    emit('3002');ref('8C','timerend');bne('timer')
    ref('7E','done')
    label('fail');emit('86FF B7020C')
    label('done');emit('1A50 4F B73FE1 CCCAFE FD020E 20FE')
    label('timers');emit('0000 00C8 FC18 FC3D');label('timerend')
    label('ccs');emit('505F707FD0DFF0FF');label('ccend')
    for offset,name,relative in fixups:
        value=labels[name]-(origin+offset+2) if relative else labels[name]
        code[offset:offset+2]=(value&0xffff).to_bytes(2,'big')
    assert image[origin+0x70000:origin+0x70000+len(code)]==b'\xff'*len(code)
    out=bytearray(image);out[origin+0x70000:origin+0x70000+len(code)]=code;out[-2:]=origin.to_bytes(2,'big')
    return bytes(out),{'origin':hex(origin),'program_hex':code.hex(),'labels':labels,'vectors':256*8*4,
                       'purpose':'CPU-only atomic stop-hook unit fixture; never burn; no game/play qualification'}

def run(folder,port):
 image=runtime.image_path().read_bytes()
 if image[0x2B040:0x2B058]==b'\xff'*24:raise ValueError('This image has no stop hook at 2A:7040; unit is not applicable')
 data,meta=fixture(image);folder.mkdir(parents=True,exist_ok=False)
 fixture_path=folder/'UNIT_ONLY_NEVER_BURN.bin';fixture_path.write_bytes(data)
 rompath=folder/'PRIVATE-roms';game=rompath/'gw_kh5';game.mkdir(parents=True)
 (game/'getaw_kh5.rom').write_bytes(data);(game/'u18snd').write_bytes(__import__('lab.config',fromlist=['sound']).sound(runtime.PROJECT))
 raw=folder/'raw-coils.jsonl'
 with emulator(Path(runtime.PROJECT['emulator']),folder/'runtime',rompath,port,io_trace=raw) as api:
  api.frames(120);memory=api.call('debugger/memory',addr='0200',size=16)['data']
  if memory[12]!=0 or memory[14:16]!=[0xCA,0xFE] or int.from_bytes(bytes(memory[10:12]),'big')!=8192:raise AssertionError('PWM vector controller did not complete cleanly')
  io=api.call('getaway/test');rows=[json.loads(s) for s in raw.read_text().splitlines()]
  writes=[r for r in rows if r['kind']=='write' and r['address']==0x3FE1]
  if len(writes)!=8192*2+1:raise AssertionError('PWM output-write count differs')
  for index in range(8192):
   a,b=writes[index*2:index*2+2];v=index%256
   if (a['value'],b['value'])!=(v,v&254) or not 0<b['time']-a['time']<.0001:raise AssertionError('Atomic stop latch/timing vector differs')
  if writes[-1]['value']!=0:raise AssertionError('Unit did not finish with high-power outputs clear')
 record=dict(result='PASS',image_name=runtime.selected(),image_sha1=hashlib.sha1(image).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),
  emulator_sha256=sha(runtime.PROJECT['emulator']),fixture_sha256=hashlib.sha256(data).hexdigest(),
  fixture_kind='UNIT_ONLY_NEVER_BURN; no gameplay or hardware qualification',catalogue_mismatch_expected=True,
  vectors=8192,shadow_values=256,CC_values=['50','5F','70','7F','D0','DF','F0','FF'],timer_values=['0000','00C8','FC18','FC3D'],
  source_nvram_unchanged=True,frames=120,final_io=io,unit=True,qualification='Native CPU/register/output vectors only')
 (folder/'result.json').write_text(json.dumps(record,indent=2)+'\n');return record

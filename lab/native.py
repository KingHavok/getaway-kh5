"""Native boot checksum; no checksum bypass or Python-only substitute."""
import time
from . import runtime

def boot(folder,port):
 data=runtime.image_path().read_bytes();expected=int.from_bytes(data[-18:-16],'big')
 with runtime.session(folder,port,__file__,unit=True) as (api,r):
  def halt(address):
   api.call('debugger/breakpoints',cmd='clear');api.call('debugger/breakpoints',cmd='add',addr=f'{address:04X}')
   api.call('debugger/control',cmd='resume');deadline=time.monotonic()+60
   while not api.call('info')['paused']:
    if time.monotonic()>deadline:raise TimeoutError('Native ROM checksum did not reach breakpoint')
    time.sleep(.01)
   cpu=api.call('debugger/state')['cpus'][0]
   if cpu['pc']!=address:raise AssertionError('Unexpected checksum stop')
   return cpu
  if api.memory(0xFFEC,4)!=data[-20:-16]:raise AssertionError('Loaded checksum words differ from declared image')
  before=halt(0x8D29)
  if (before['a']<<8|before['b'])!=expected:raise AssertionError('Native computed sum differs')
  after=halt(0x8D30)
  if after['a'] or after['b']:raise AssertionError('Native ROM test did not take zero-difference success branch')
  api.call('debugger/breakpoints',cmd='clear')
  r.update(result='PASS',native_checksum=f'{expected:04X}',native_success_PC='8D30',checksum_bypassed=False,
           qualification='Native reset checksum computation; resume/breakpoints, not frame-budget gameplay')

"""Authored state-aware API; all raw responses remain private."""
import json,time,urllib.parse,urllib.request
class API:
    def __init__(self, port, log, unit=False):
        self.port, self.log, self.frames_run = port, log, 0
        self.unit=unit

    def call(self, path, **params):
        if not self.unit and path=='debugger/state/write':raise ValueError('CPU mutation is reserved for explicit unit fixtures')
        if not self.unit and path=='debugger/control' and params.get('cmd') in ['reset','step','resume']:raise ValueError('Gameplay sessions require bounded frames')
        if not self.unit and path=='debugger/memory/write':
            address=int(params['addr'],16);payload=bytes.fromhex(params['data'])
            if not (address==0x3FFD and payload in [b'\xb4',b'\0'] or 0x1B1D<=address<0x1BDF and (address-0x1B1D)%2==0 and len(payload)==2):raise ValueError('Gameplay write outside operator CMOS setup')
        url = f'http://127.0.0.1:{self.port}/api/{path}?' + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.load(response)
        if data.get('status') == 'error':
            raise RuntimeError(data)
        saved = data
        if path == 'debugger/memory':
            saved = {'addr': params['addr'], 'data_hex': bytes(data['data']).hex()}
        self.log.write(json.dumps({'frame_budget_total': self.frames_run,
                                   'path': path, 'params': params, 'response': saved}) + '\n')
        self.log.flush()
        return data

    def memory(self, addr, size):
        return bytes(self.call('debugger/memory', addr=f'{addr:04X}', size=size)['data'])

    def frames(self, count):
        if count>600:
            while count:
                part=min(count,600);self.frames(part);count-=part
            return
        assert 0 < count <= 600
        self.call('debugger/control', cmd='frames', count=count)
        deadline = time.monotonic() + 60
        while True:
            state = self.call('info')
            if state['paused']:
                assert state['frames_remaining'] == 0
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Frame budget did not complete')
            time.sleep(.01)
        self.frames_run += count

    def pulse(self, port, value, on=6, after=0):
        self.call('input/port', port=port, val=value)
        self.frames(on)
        self.call('input/port', port=port, val='0')
        if after:
            self.frames(after)

    def button(self, mask, on=6, after=0):
        self.call('input/button', mask=mask, val=1)
        self.frames(on)
        self.call('input/button', mask=mask, val=0)
        if after:
            self.frames(after)

    def state(self, tasks=False):
        low, high = self.memory(0, 2048), self.memory(0x800, 2048)
        switches = self.call('switches')['switches']
        result = {'player': low[0x40F], 'ball': low[0x410], 'phase': list(low[0x8C:0x8F]),
                  'validated': low[0x416], 'live': high[6], 'qualified': high[5],
                  'lock_credits': [high[0x128 + p * 54] for p in range(4)],
                  'gears': [high[0x12C + p * 54] for p in range(4)],
                  'switches': {s['num']: s['active'] for s in switches}}
        if tasks:
            ram = low + high + self.memory(0x1000, 2048) + self.memory(0x1800, 2048)
            ids = []
            for head in [0x366, 0x371]:
                pointer = int.from_bytes(ram[head:head + 2], 'big')
                visited = set()
                while pointer:
                    assert pointer not in visited and 0x300 <= pointer <= 0x1FD3, ('Invalid task chain', head, pointer)
                    visited.add(pointer)
                    assert len(visited) <= 128
                    ids.append(int.from_bytes(ram[pointer + 0x11:pointer + 0x13], 'big') & 0x1FF)
                    pointer = int.from_bytes(ram[pointer:pointer + 2], 'big')
            result['task_ids'] = ids
        return result

    def wait(self, label, predicate, limit=1800, step=30, tasks=False, activity=False):
        elapsed = 0
        next_activity = 240
        while True:
            state = self.state(tasks)
            if predicate(state):
                return state
            if elapsed >= limit:
                raise TimeoutError((label, state))
            if activity and elapsed >= next_activity:
                self.pulse(4, '12', after=180)
                elapsed += 186
                next_activity = elapsed + 240
            count = min(step, limit - elapsed)
            if count <= 0:
                raise TimeoutError(label)
            self.frames(count)
            elapsed += count
    def io(self):return self.call('getaway/test')
    def fault(self,kind,id,value):return self.call('getaway/test',cmd='set',kind=kind,id=id,val=value)
    def marker(self,name):
        item=dict(io=self.io(),state=self.state(tasks=True))
        self.log.write(json.dumps(dict(frame_budget_total=self.frames_run,path='lab/marker',params=dict(name=name),response=item))+'\n');self.log.flush()
        return item

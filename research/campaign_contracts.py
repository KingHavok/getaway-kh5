"""Portable audit of declared state/provenance/fault contracts, plus raw coil edges.
Retains the historical short-case clock check; pulse widths are not given a widened margin.
"""
import hashlib,json,pathlib
from lab.config import REPO as ROOT
from analyze_coil_trace import analyze,ANALYZER_SHA256
def obj(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def sensor(io,n):return next(x for x in io['switches'] if x['id']==n)

def audit(folder,coils=False,specification=None):
    r=obj(folder/'result.json');assert r['result']=='PASS'
    if specification is not None:r.setdefault('specification',specification)
    from lab.runtime import PROJECT
    from lab.config import verify_image
    entry,_=verify_image(PROJECT,r['image_name'])
    assert r['image_sha256']==entry['identity']['sha256']
    assert hashlib.sha1(pathlib.Path(r['rom_file']).read_bytes()).hexdigest()==r['image_sha1']
    assert r['emulator_sha256']==sha(PROJECT['emulator'])
    assert r['source_nvram_unchanged'] and sha(pathlib.Path(r['nvram_seed_path']))==r['initial_nvram_sha256']
    assert r['rtc']=='2026-11-08 12:00:00' and r['sound_cpu_enabled']
    assert r['session_source_sha256']==sha(ROOT/'lab/runtime.py')
    assert r['test_source_sha256'] in {sha(p) for p in (ROOT/'research').glob('*.py')}|{sha(p) for p in (ROOT/'lab').glob('*.py')}
    if r.get('contract_source'):assert r['contract_source_sha256']==sha(pathlib.Path(r['contract_source']))
    frames=0;markers={}
    for line in (folder/'actions.jsonl').open():
        a=json.loads(line);path=a['path'];params=a['params']
        assert path not in ['debugger/state/write','debugger/savestate','debugger/memory/fill']
        if path=='debugger/control':
            assert params['cmd'] in ['frames','exit']
            if params['cmd']=='frames':frames+=params['count']
        elif path=='debugger/memory/write':
            address=int(params['addr'],16);data=bytes.fromhex(params['data'])
            assert ((address==0x3FFD and data in [b'\xb4',b'\0']) or
                    (0x1B1D<=address<0x1BDF and (address-0x1B1D)%2==0 and len(data)==2))
        elif path=='lab/marker':
            snap=a['response'];markers[params['name']]=snap
            assert len([b for b in snap['io']['balls'] if b['installed']])==3
            assert snap['state']['live']<=3
    assert frames==r['frames']
    delta=r['final_io']['time']-frames/60
    assert min(abs(delta),abs(delta+1/60))<1e-7,('Clock consistency diagnostic',delta)
    s=r['specification'];kind=s.get('kind')
    if kind in ['switch','mechanism']:
        assert r['fault_exercised'] and r['post_repair_lock_ok']
        a,b=r['injection'],r['faulted']['io'];n=s['id']
        if kind=='switch':
            assert sensor(b,n)['changed_reads']>sensor(a,n)['changed_reads']
            assert sensor(b,n)['last_seen']==sensor(b,n)['forced']==s['value']
        else:
            m=next(x for x in b['mechanisms'] if x['id']==n)
            assert m['forced_response']==s['value'] and m['changed_observations']>0
        repair=markers['post-repair-next-turn-lock']
        assert any(repair['state']['switches'][str(n)] for n in [74,75,76]) or repair['state']['live']==3
    elif 'scenario' in s:
        assert sensor(r['before']['io'],54)['physical']==1
        assert sensor(r['first_passage_lift']['io'],54)['physical']==0
        if s['scenario']!='fast':
            assert sensor(r['trapped']['io'],54)['physical']==1
            assert sensor(r['release_lift']['io'],54)['physical']==0
        assert r['found']['state']['lock_credits'][0]==s['locks']
        assert r['final']['state']['lock_credits'][0]==s['locks']+1 or r['final']['state']['live']==3
    elif kind=='flipper':
        f=s['flipper'];held=r['held'];stopped=r['stopped']
        assert held['state']['phase']==[0,0,0] and held['state']['live']==1
        assert not((~held['io']['raw_registers'][4])&(1<<f['stroke']))
        assert (~held['io']['raw_registers'][4])&(1<<f['hold'])
        assert ((~stopped['io']['raw_registers'][4])&63)==0
        if s['forced']>=0:
            assert sensor(held['io'],f['eos'])['changed_reads']>sensor(r['before']['io'],f['eos'])['changed_reads']
        if s['shutdown']=='slam':
            log=obj(folder/'shutdown-traces.json')['log']
            assert sum((t['pc'],t['bank'])==(0x5F96,0x39) for t in log)==1
            assert any((t['pc'],t['bank'])==(0x5FCB,0x39) for t in log)
            assert any(t['pc']==0x8E79 for t in log)
    elif kind=='firing-switch':
        n=s['switch'];assert sensor(r['faulted']['io'],n)['changed_reads']>sensor(r['before']['io'],n)['changed_reads']
        assert sensor(r['faulted']['io'],n)['last_seen']==s['forced']
        assert r['positive']['io']['time']>r['repaired']['io']['time']
    else:
        traces=obj(folder/'traces.json')['log'];assert len(traces)<512
        owner,recipient=s['owner'],s['recipient'];mode=s['mode'];ending=s['ending']
        normal=[t for t in traces if (t['pc'],t['bank'])==(0x6253,0x2A)]
        red=[t for t in traces if (t['pc'],t['bank'])==(0x6A88,0x2A)]
        assert [bytes.fromhex(t['ram'])[0x40F] for t in normal]==(([recipient] if mode!='redline' else [])+([owner] if ending!='restart' else []))
        assert [bytes.fromhex(t['ram'])[0x40F] for t in red]==([recipient] if mode=='redline' else [])
        if mode=='burn':
            award=next(t for t in normal if bytes.fromhex(t['ram'])[0x40F]==recipient)
            assert bytes.fromhex(award['ram'])[0x937+54*(recipient-1)]==5,'MB was not the actual fifth Burn Rubber award'
        if mode=='redline':
            init=[t for t in traces if (t['pc'],t['bank'])==(0x6AD4,0x2A)];assert len(init)==1
            ram=bytes.fromhex(init[0]['ram']);assert ram[0x8C:0x8F]==b'\0\0\0'
            assert ram[0x40F:0x411]==bytes.fromhex(red[0]['ram'])[0x40F:0x411]
        if ending=='restart':
            reset=[t for t in traces if (t['pc'],t['bank'])==(0x45A4,0x38)];assert len(reset)==1
            assert not any((t['pc'],t['bank'])==(0x6AD4,0x2A) and t['time']>reset[0]['time'] for t in traces)
            clean=markers['restart-physical-inventory-settled']['state']
            assert (clean['player'],clean['ball'],clean['live'],clean['phase'])==(1,1,1,[0,0,0])
            assert sum(clean['switches'][str(n)] for n in [56,57,58])==2
            assert clean['lock_credits'][:s['players']]==[0]*s['players']
            assert not({0xF2,0xF3,0xB7,0x138,0x139}&set(clean['task_ids'])),'Prior mode task survived restart'
        else:
            saved=r['saved_owner'];back=r['owner_returned'].get('state',r['owner_returned'])
            assert back['lock_credits'][owner-1]==saved['credits']==s['locks']
            assert back['gears'][owner-1]==saved['gear'] and back['qualified']==saved['qualified']
    if 'final' in r and 'io' in r['final']:
        io=r['final']['io']
        assert all(x['forced']==-1 for x in io['switches'])
        assert all(x['forced_response']==-1 for x in io['mechanisms'])
    result=dict(folder=str(folder),game=r['game'],specification=s,frames=frames)
    if coils:
        path=folder/'coil-analysis.json'
        measured=obj(path) if path.exists() else None
        if not measured or measured.get('analyzer_sha256')!=ANALYZER_SHA256:
            measured=analyze(folder);path.write_text(json.dumps(measured,indent=2)+'\n')
        assert measured['image_sha1']==r['image_sha1'] and measured['writes_verified']==r['final_io']['write_count']
        result['coil_analysis_sha256']=sha(path)
        result['pulse_maxima']={k:v['longest_on_seconds'] for k,v in measured['coils'].items() if v['category'] in ['pulse coil','flipper stroke'] and v['activations']}
        result['ramp_overlaps']=measured['ramp_opposing_command_overlaps']
        assert result['ramp_overlaps']['count']==0,'Opposing ramp commands require review'
    return result

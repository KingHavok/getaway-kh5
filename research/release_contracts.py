"""Independent positive award/progression assertions ported from the release audit."""
import json
def obj(p):return json.loads(p.read_text())
def trace(folder,name):return obj(folder/name)["log"]
def snapshots(rows):return {r["params"]["name"]:r["response"] for r in rows if r["path"]=="lab/marker"}
def memory_at_markers(rows):
 ram=bytearray(8192);found={}
 for r in rows:
  if r['path']=='debugger/memory':
   addr=int(r['params']['addr'],16);data=bytes.fromhex(r['response']['data_hex']);ram[addr:addr+len(data)]=data
  if r['path']=='lab/marker':found[r['params']['name']]=bytes(ram)
 return found

def contract(name,r,rows,folder):
 m=snapshots(rows);result={}
 if name.startswith('mixed-v2'):
  players=r['players'];balls=5 if r['kids'] else 3
  assert [(t['ball'],t['player']) for t in r['new_game_turns']]==[(b,p) for b in range(1,balls+1) for p in range(1,players+1)]
  final=r['final']['state'];assert final['phase']==[0,1,0] and final['live']==0
  assert all(final['switches'][str(s)] for s in [56,57,58])
  assert not any(final['switches'][str(s)] for s in [74,75,76,78])
  starts=trace(folder,'recipient-start.traces.json');assert sum(t['pc']==0x6253 for t in starts)==1
  rec=3 if r['kids'] else 2;assert bytes.fromhex(next(t for t in starts if t['pc']==0x6253)['ram'])[0x40f]==rec
  assert all(m[f'award-{i}']['state']['live']==3 for i in range(3))
  for i in range(3):assert not any(t['pc']==0x6253 for t in trace(folder,f'award-{i}.traces.json'))
  red=trace(folder,'redline-start.traces.json');assert sum(t['pc']==0x6AD4 for t in red)==1
  ram=memory_at_markers(rows);observed=[ram[f'award-{i}'][0x931+54*(rec-1)] for i in range(3)]
  assert observed==[0,1,2],observed
  result.update(contract='Mixed multiplayer, shared locks, three award shots, Redline, tilt, restart, full new game and physical return',players=players,ordinary_turns=len(r['new_game_turns']),observed_progress_field=[hex(0x931+54*(rec-1)),observed],scoring_limit='Award progress and absence of restarts observed; no claim that the unused F441 trace measures actual score payout')
 elif name.startswith('awards-v3'):
  a=r['before_collection']['state'];b=r['after_collection']['state'];assert a['phase']==b['phase']==[0,0,0]
  t=trace(folder,'native-awards.traces.json');eb=[x for x in t if x['pc']==0xB4C4];assert len(eb)==1
  assert bytes.fromhex(eb[0]['ram'])[0x411:0x413]==b'\0\0'
  ram=memory_at_markers(rows);assert ram['tunnel-award-collected'][0x411:0x413]==b'\1\1'
  assert sum(x['pc']==0x56CB for x in t)==sum(x['pc']==0x5730 for x in t)==sum(x['pc']==0x5776 for x in t)==1
  result.update(contract='Retained Secret Mania challenge and real tunnel extra-ball collection',credited_extra_balls=1)
 elif name.startswith('special-v1'):
  assert r['shots']==8 and r['knocker_activations']>0
  shots=obj(folder/'shots.json');assert [x['special_lit'] for x in shots]==[False]*7+[True]
  events=obj(folder/'award-events.json');assert any(e['type']=='sol' and e['id']==7 and e['val'] for e in events)
  def lamp(s):return bool(bytes.fromhex(s)[2]&16)
  # Physical lamp 21 maps logical SPECIAL (2), independently of DMD text.
  def near_ram(label):return memory_at_markers(rows)[label]
  assert near_ram('special-lit-before-outlane')[0x2e2]&16
  assert not (near_ram('special-outlane-collected')[0x2e2]&16)
  result.update(contract='Special lights after eight tunnel shots and is consumed at right outlane with real positive award output',knocker_activations=r['knocker_activations'])
 elif name.startswith('casual-v1'):
  t=trace(folder,'native-selection.traces.json');selected=[x for x in t if (x['pc'],x['bank'])==(0x5D3B,0x2A)]
  assert len(selected)==1 and any(x['pc']==0x7317 and x['bank']==0x36 for x in t)
  assert r['burn_rubber_count']==1 and r['native_selected_id']==bytes.fromhex(selected[0]['ram'])[0x89d]==16
  assert sum(x['pc']==0x6253 for x in t)==1 and r['after_award']['state']['live']==3
  result.update(contract='Native non-tournament Burn Rubber selection and resulting multiball',selected_native_award_id=16,kids=r['kids'],scope='One deterministic award per profile; other random awards not inferred')
 elif name.startswith('exploration-v'):
  assert not any(x['path']=='debugger/memory/write' for x in rows)
  settings={}
  for x in rows:
   if x['path']=='debugger/memory' and x['params']['size']==2:
    settings[x['params']['addr']]=int.from_bytes(bytes.fromhex(x['response']['data_hex']),'big')
  kids=name=='exploration-v2/menu';expected={'1B1F':5 if kids else 3,'1B39':3,'1B9D':1,'1BCB':99 if kids else 20,'1BD5':99 if kids else 20}
  assert all(settings[k]==v for k,v in expected.items())
  assert any(x['path']=='input/button' and x['params']['mask']=='80' for x in rows)
  result.update(contract='Actual native service-button changes; original exploration status retained and independently qualified here',settings=expected)
 elif name.startswith('service-persistence'):
  assert not any(x['path']=='debugger/memory/write' for x in rows)
  assert r['cold_boot']['state']['phase']==[0,1,0]
  assert r['started']['state']['phase']==[0,0,0] and r['started']['state']['live']==1
  result.update(contract='Fresh process, retained operator words, free-play game start',settings=r['settings'])
 elif name.startswith('video-v11'):
  t=trace(folder,'native-video.traces.json');assert any(x['pc']==0x6B7F for x in t) and not any(x['pc']==0x70EA for x in t)
  assert r['final']['state']['live']==1 and r['final']['state']['phase']==[0,0,0]
  result.update(contract='Native video gameplay completes without collision and returns to one-ball play; no video extra ball in this run')
 elif name.startswith('video-v12'):
  t=trace(folder,'native-video.traces.json');assert sum(x['pc']==0x70D9 and x['bank']==0x24 for x in t)==1
  eb=[x for x in t if x['pc']==0xB4C4];assert len(eb)==1 and bytes.fromhex(eb[0]['ram'])[0x411:0x413]==b'\0\0'
  assert r['credited_extra_balls']=='0101';assert r['final']['state']['phase']==[0,0,0] and r['final']['state']['live']==1
  result.update(contract='Native video target collision, real extra-ball counter increments, natural video exit and one-ball return',credited_extra_balls=1)
 else:raise AssertionError(name)
 return result

"""Compare matching completed digital-pulse contracts; never infer thermal safety."""
import json,math
from pathlib import Path

def compare(reference,target,margin=1e-5):
 if not math.isfinite(margin) or margin<0:raise ValueError('Margin must be non-negative')
 before=json.loads(Path(reference).read_text());after=json.loads(Path(target).read_text())
 left={c['id']:c for c in before['cases']};right={c['id']:c for c in after['cases']};flags=[];pairs=[]
 for label,summary in [('reference',before),('target',after)]:
  if summary.get('result')!='PASS' or summary.get('planned',len(summary['cases']))!=len(summary['cases']):flags.append(dict(kind='Incomplete or non-passing summary',side=label))
  if len({c['id'] for c in summary['cases']})!=len(summary['cases']):flags.append(dict(kind='Duplicate case IDs',side=label))
 if set(left)!=set(right):flags.append(dict(kind='unmatched cases',reference_only=sorted(set(left)-set(right)),target_only=sorted(set(right)-set(left))))
 for name in sorted(set(left)&set(right)):
  a,b=left[name],right[name]
  if a['result']!='PASS' or b['result']!='PASS':flags.append(dict(case=name,kind='Incomplete or flagged input contract'));continue
  if 'specification' not in a or 'specification' not in b or a['specification']!=b['specification'] or a.get('group')!=b.get('group'):flags.append(dict(case=name,kind='Missing or unequal stimulus specifications'));continue
  aa=a['audit'];bb=b['audit'];x=aa.get('pulse_maxima_seconds',aa.get('pulse_maxima',{}));y=bb.get('pulse_maxima_seconds',bb.get('pulse_maxima',{}))
  if not x or not y:flags.append(dict(case=name,kind='No measured pulse comparison'));continue
  outputs=[]
  for output in sorted(set(x)|set(y)):
   if any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in [x.get(output,0),y.get(output,0)]):raise ValueError('Invalid observed pulse duration')
   delta=y.get(output,0)-x.get(output,0)
   row=dict(output=output,reference_seconds=x.get(output,0),target_seconds=y.get(output,0),difference_seconds=delta)
   outputs.append(row)
   if delta>margin:flags.append(dict(case=name,kind='Observed pulse exceeds reference plus explicit comparison margin',**row))
  pairs.append(dict(case=name,reference_image=a['image'],target_image=b['image'],outputs=outputs))
 return dict(result='FLAGGED' if flags or not pairs else 'PASS',matched_pairs=len(pairs),margin_seconds=margin,flags=flags,pairs=pairs,
  limits=['Digital observed maxima under the selected completed contracts, not physical current/heat or a certified safe pulse width','A flag requires event/timing review; never widen a margin simply to turn a flag green'])

#!/usr/bin/env python3
"""Compare two private campaign summaries, preserving unmatched/failing cases."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lab.compare import compare
from lab.config import private_path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--target',type=Path,required=True);p.add_argument('--margin',type=float,default=1e-5);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
private_path(a.output)
x=compare(a.reference,a.target,a.margin)
with a.output.open('x') as f:json.dump(x,f,indent=2)
print(x['result'],x['matched_pairs'],'matched pulse comparisons');sys.exit(x['result']!='PASS')

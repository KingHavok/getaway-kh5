#!/usr/bin/env python3
"""Convert a user-supplied official raw L5 U6 into the exact KH5 release."""
import argparse,csv,json,os
from pathlib import Path
from kh5patch.core import convert,identity

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--log',type=Path,help='Optional PRIVATE every-byte before/after CSV; never commit this log')
    args=parser.parse_args()
    try:
        if args.input.resolve()==args.output.resolve():raise ValueError('Input and output must differ')
        if args.log and args.log.resolve() in [args.input.resolve(),args.output.resolve()]:raise ValueError('Log must differ from input and output')
        if args.log and not args.log.parent.is_dir():raise ValueError('Log parent directory does not exist')
        if args.output.exists() or args.log and args.log.exists():raise ValueError('Refusing to overwrite an existing output or log')
        data=args.input.read_bytes();target,regions=convert(data)
        # Verification finishes before any output file is created. Exclusive create
        # also prevents overwrites when another process races this command.
        with args.output.open('xb') as f:f.write(target)
        if args.log:
            with args.log.open('x',newline='') as f:
                w=csv.writer(f);w.writerow(['file_offset','bank','cpu_address','before','after','change'])
                for i,(a,b) in enumerate(zip(data,target)):
                    if a==b:continue
                    group=next((name for start,end,name in regions if start<=i<end),'CHECKSUM')
                    fixed=i>=0x78000;pc=i-0x70000 if fixed else 0x4000+i%0x4000
                    w.writerow([f'{i:05X}','FIXED' if fixed else f'{(i//0x4000)|0x20:02X}',f'{pc:04X}',f'{a:02X}',f'{b:02X}',group])
        print(json.dumps(dict(revision='KH5',output=str(args.output),**identity(target)),indent=2))
    except (ValueError,OSError,KeyError) as e:parser.exit(1,f'Conversion refused: {e}\n')
if __name__=='__main__':main()

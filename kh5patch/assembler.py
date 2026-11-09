"""Small deterministic assembler for the reviewed patch, not a general 6809 tool."""
from pathlib import Path

REGISTERS = {"CC":1,"A":2,"B":4,"D":6,"DP":8,"X":16,"Y":32,"U":64,"PC":128}

def number(value):
    return int(value.removeprefix("$").strip(), 16)

def assemble(path):
    labels={};rows=[];pc=0
    for raw in Path(path).read_text().splitlines():
        line=raw.split(';',1)[0].strip()
        if not line:continue
        if line.lower().startswith('.org '):pc=number(line.split()[1]);continue
        if line.endswith(':'):
            name=line[:-1]
            if name in labels:raise ValueError('Duplicate label')
            labels[name]=pc;continue
        parts=line.split(None,1);op=parts[0].upper();arg=parts[1].replace(' ','') if len(parts)>1 else ''
        if op in ['PSHS','PULS','ORCC','ANDA','BEQ','BNE','BCC'] or arg.startswith('<'):size=2
        elif op in ['DECA','RTS','NOP']:size=1
        elif op=='.WORD':size=2
        elif op in ['JSR','JMP','LDA','LDX','LDD','STA']:size=3
        else:raise ValueError(f'Unsupported patch instruction: {line}')
        rows.append(dict(pc=pc,op=op,arg=arg,size=size));pc+=size
    result=[]
    for row in rows:
        op,arg,pc=row['op'],row['arg'],row['pc']
        if op in ['PSHS','PULS']:
            mask=0
            for r in arg.split(','):mask|=REGISTERS[r]
            data=bytes([0x34 if op=='PSHS' else 0x35,mask])
        elif op in ['BEQ','BNE','BCC']:
            delta=labels[arg]-(pc+2)
            if not -128<=delta<=127:raise ValueError('Branch range')
            data=bytes([{'BEQ':0x27,'BNE':0x26,'BCC':0x24}[op],delta&255])
        elif op in ['DECA','RTS','NOP']:data=bytes([{'DECA':0x4a,'RTS':0x39,'NOP':0x12}[op]])
        elif op=='.WORD':data=number(arg).to_bytes(2,'big')
        elif op in ['ORCC','ANDA']:data=bytes([{'ORCC':0x1a,'ANDA':0x84}[op],number(arg[1:])])
        elif arg.startswith('<'):data=bytes([{'STD':0xdd,'LDA':0x96,'STA':0x97}[op],number(arg[1:])])
        else:
            immediate=arg.startswith('#');value=number(arg[1:] if immediate else arg)
            opcode={'JSR':0xbd,'JMP':0x7e,'LDA':0xb6,'STA':0xb7,'LDX':0x8e,'LDD':0xcc}[op]
            data=bytes([opcode])+value.to_bytes(2,'big')
        if len(data)!=row['size']:raise ValueError('Assembler size mismatch')
        result.append(dict(row,data=data))
    segments=[]
    for row in result:
        if not segments or segments[-1]['offset']+len(segments[-1]['data'])!=0x28000+row['pc']-0x4000:
            segments.append(dict(offset=0x28000+row['pc']-0x4000,data=bytearray()))
        segments[-1]['data'].extend(row['data'])
    return [(s['offset'],bytes(s['data'])) for s in segments],result

"""Owner-local V2 lamp-driver transformation, derived from wpclp 1.4 (GPL).

No native driver signature or relocated native instruction payload is stored here.
All moved bytes are read from the supplied, hash-verified owner's ROM.
"""
START = 0x7DCF5
END = 0x67
COMPRESS = (31, 36, 42, 46)


def transform(image):
    out = bytearray(image)
    # Four indexed loads use signed offsets below 128. Compress their 16-bit
    # displacement to 8 bits; shrinking each instruction frees one byte.
    for position in COMPRESS:
        displacement = int.from_bytes(out[START+position+2:START+position+4], 'big')
        if displacement >= 128:
            raise ValueError('Unsupported V2 indexed displacement')
    for removed, position in enumerate(COMPRESS):
        out[START+position+1-removed] = 0x88
        for destination in range(START+position+2-removed, START+64):
            out[destination] = out[destination+1]
    # Change final stores to select rows before columns.
    for relative, value in ((END-6, 0xF7), (END-4, 0xE4),
                            (END-3, 0xB7), (END-1, 0xE5)):
        out[START+relative] = value
    # Move the owner's intervening instructions down three bytes, backwards to
    # preserve overlapping source. Remove the old three-byte clear instruction.
    for relative in range(END-7, END-37, -1):
        out[START+relative] = out[START+relative-3]
    # New blanking sequence: CLRB; STB $3FE5; STB $3FE4.
    out[START+60:START+67] = bytes((0x5F, 0xF7, 0x3F, 0xE5, 0xF7, 0x3F, 0xE4))
    return bytes(out)

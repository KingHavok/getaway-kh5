; Original KH5 patch routines. Motorola 6809; all numbers hexadecimal.
; This file contains added patch code only, never a disassembly of Williams ROM.
; Bank 2A: CPU 4000..7FFF maps to file 28000..2BFFF.
; The numeric predicate was identified through Soren's L-5C work; this is a new
; implementation, not its byte-for-byte 28-byte trampoline.

.org $6F98
numeric_guard:
    PSHS D             ; preserve caller D and the continuation's stack contract
    LDA $0805          ; currently qualified locks
    BEQ numeric_reject ; no qualification: return to the caller
    LDA $0806          ; live balls
    DECA               ; reject unless precisely one; retain DECB-equivalent flags
    BNE numeric_reject
    PULS D             ; recover original D before replaying the displaced prologue
    PSHS D             ; continuation 6096 expects this saved D on its stack
    JSR $6EC6          ; existing native game-state predicate, read from owner's ROM
    JMP $6096          ; resume original routine after the displaced prologue
numeric_reject:
    PULS D,PC          ; reject with original D and caller return stack restored

.org $6FD0
pending_guard:
    PSHS D
    JSR $86BF          ; native task lookup consumes the following inline task word
    .word $00F2        ; pending Redline introduction; not running F3
    BCC pending_reject ; this lookup returns carry clear for a present task
    PULS D
    JMP $6F98          ; preserve qualified one-ball locks after Getaway grace
pending_reject:
    PULS D
    RTS

.org $7000
secret_guard:
    PSHS D,X
    JSR $86BF
    .word $0138        ; actual Secret Mania gameplay/preparation task
    BCC secret_reject
    JSR $86BF
    .word $0139        ; Secret Mania result task also owns the backup
    BCC secret_reject
    LDX #$08E2         ; establish the native prologue's expected accumulator pointer
    JMP $56CB          ; retain all native gameplay, display, scoring and challenge
secret_reject:
    PULS D,X,PC

.org $7040
pwm_stop:
    PSHS CC
    ORCC #$50          ; mask IRQ and FIRQ across timer/shadow/hardware updates
    LDD #$0000
    STD <$E6           ; clear the two-byte native PWM timer
    LDA <$7C           ; low-power-bank shadow includes seven unrelated output bits
    ANDA #$FE          ; clear diverter-high bit 0 only
    STA <$7C
    STA $3FE1          ; clear the actual high-power latch in the same atomic window
    PULS CC            ; restore original interrupt masks and carry
    LDD #$0000         ; reproduce native return D=0 and N/Z/V effects
    RTS

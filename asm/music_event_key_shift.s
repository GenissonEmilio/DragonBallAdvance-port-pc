/* USA 0x0810A5F4: explicit SDK assembly, excluded from C matching counts. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_KeyShift
.type MusicEvent_KeyShift,%function
.thumb_func
MusicEvent_KeyShift:
    mov r12, lr
    bl Music_ReadCommandFiltered
    strb r3, [r1, #0x0A]
    ldrb r3, [r1]
    movs r2, #0x0C
    orrs r3, r2
    strb r3, [r1]
    bx r12
    .balign 4,0
.size MusicEvent_KeyShift,.-MusicEvent_KeyShift

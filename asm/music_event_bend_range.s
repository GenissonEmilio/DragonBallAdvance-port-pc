/* USA 0x0810A674: SDK assembly; counted separately from matching C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_BendRange
.type MusicEvent_BendRange,%function
.thumb_func
MusicEvent_BendRange:
    mov r12, lr
    bl Music_ReadCommandFiltered
    strb r3, [r1, #0x0F]
    ldrb r3, [r1]
    movs r2, #0x0C
    orrs r3, r2
    strb r3, [r1]
    bx r12
.align 2,0
.size MusicEvent_BendRange,.-MusicEvent_BendRange

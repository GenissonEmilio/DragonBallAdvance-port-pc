/* USA 0x0810A660: SDK assembly; counted separately from matching C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_PitchBend
.type MusicEvent_PitchBend,%function
.thumb_func
MusicEvent_PitchBend:
    mov r12, lr
    bl Music_ReadCommandFiltered
    subs r3, #0x40
    strb r3, [r1, #0x0E]
    ldrb r3, [r1]
    movs r2, #0x0C
    orrs r3, r2
    strb r3, [r1]
    bx r12
.size MusicEvent_PitchBend,.-MusicEvent_PitchBend

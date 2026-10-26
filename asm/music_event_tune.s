/* USA 0x0810A6AC: SDK assembly; counted separately from matching C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_Tune
.type MusicEvent_Tune,%function
.thumb_func
MusicEvent_Tune:
    mov r12, lr
    bl Music_ReadCommandFiltered
    subs r3, #0x40
    strb r3, [r1, #0x0C]
    ldrb r3, [r1]
    movs r2, #0x0C
    orrs r3, r2
    strb r3, [r1]
    bx r12
.size MusicEvent_Tune,.-MusicEvent_Tune

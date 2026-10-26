/* USA 0x0810A64C: SDK assembly; counted separately from matching C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_Pan
.type MusicEvent_Pan,%function
.thumb_func
MusicEvent_Pan:
    mov r12, lr
    bl Music_ReadCommandFiltered
    subs r3, #0x40
    strb r3, [r1, #0x14]
    ldrb r3, [r1]
    movs r2, #0x03
    orrs r3, r2
    strb r3, [r1]
    bx r12
.size MusicEvent_Pan,.-MusicEvent_Pan

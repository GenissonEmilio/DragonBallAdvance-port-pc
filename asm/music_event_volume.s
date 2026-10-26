/* USA 0x0810A638: SDK assembly; counted separately from matching C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_Volume
.type MusicEvent_Volume,%function
.thumb_func
MusicEvent_Volume:
    mov r12, lr
    bl Music_ReadCommandFiltered
    strb r3, [r1, #0x12]
    ldrb r3, [r1]
    movs r2, #0x03
    orrs r3, r2
    strb r3, [r1]
    bx r12
    .balign 4,0
.size MusicEvent_Volume,.-MusicEvent_Volume

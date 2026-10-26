/* USA 0x0810A688: SDK assembly; counted separately from matching C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_LfoDelay
.type MusicEvent_LfoDelay,%function
.thumb_func
MusicEvent_LfoDelay:
    mov r12, lr
    bl Music_ReadCommandFiltered
    strb r3, [r1, #0x1B]
    bx r12
.align 2,0
.size MusicEvent_LfoDelay,.-MusicEvent_LfoDelay

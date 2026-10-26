/* USA 0x0810A608: SDK assembly; counted separately from matching C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_Voice
.type MusicEvent_Voice,%function
.thumb_func
MusicEvent_Voice:
    mov r12, lr
    ldr r2, [r1, #0x40]
    ldrb r3, [r2]
    adds r2, #1
    str r2, [r1, #0x40]
    lsls r2, r3, #1
    adds r2, r2, r3
    lsls r2, r2, #2
    ldr r3, [r0, #0x30]
    adds r2, r2, r3
    ldr r3, [r2]
    bl Sound_FilterAddress
    str r3, [r1, #0x24]
    ldr r3, [r2, #4]
    bl Sound_FilterAddress
    str r3, [r1, #0x28]
    ldr r3, [r2, #8]
    bl Sound_FilterAddress
    str r3, [r1, #0x2C]
    bx r12
    .balign 4,0
.size MusicEvent_Voice,.-MusicEvent_Voice

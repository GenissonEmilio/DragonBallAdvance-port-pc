/* USA: explicit SDK assembly, excluded from C matching counts. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_Pattern
.type MusicEvent_Pattern,%function
.thumb_func
MusicEvent_Pattern:
    ldrb r2, [r1, #2]
    cmp r2, #3
    bhs overflow
    lsls r2, #2
    adds r3, r1, r2
    ldr r2, [r1, #0x40]
    adds r2, #4
    str r2, [r3, #0x44]
    ldrb r2, [r1, #2]
    adds r2, #1
    strb r2, [r1, #2]
    b MusicEvent_Goto
overflow:
    b MusicEvent_Fine
    .balign 4,0
.size MusicEvent_Pattern,.-MusicEvent_Pattern

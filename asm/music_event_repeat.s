/* USA: explicit SDK assembly, excluded from C matching counts. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_Repeat
.type MusicEvent_Repeat,%function
.thumb_func
MusicEvent_Repeat:
    push {lr}
    ldr r2, [r1, #0x40]
    ldrb r3, [r2]
    cmp r3, #0
    bne finite
    adds r2, #1
    str r2, [r1, #0x40]
    b MusicEvent_GotoBody
finite:
    ldrb r3, [r1, #3]
    adds r3, #1
    strb r3, [r1, #3]
    mov r12, r3
    bl Music_ReadCommandFiltered
    cmp r12, r3
    bhs complete
    b MusicEvent_GotoBody
complete:
    movs r3, #0
    strb r3, [r1, #3]
    adds r2, #5
    str r2, [r1, #0x40]
    pop {r0}
    bx r0
    .balign 4,0
.size MusicEvent_Repeat,.-MusicEvent_Repeat

/* Explicit SDK assembly; excluded from C matching counts. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_Priority
.type MusicEvent_Priority,%function
.thumb_func
MusicEvent_Priority:
    mov r12, lr
    bl Music_ReadCommandFiltered
    strb r3, [r1, #0x1D]
    bx r12
    .balign 4,0
.size MusicEvent_Priority,.-MusicEvent_Priority

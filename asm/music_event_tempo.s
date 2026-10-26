/* Explicit SDK assembly; excluded from C matching counts. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_Tempo
.type MusicEvent_Tempo,%function
.thumb_func
MusicEvent_Tempo:
    mov r12, lr
    bl Music_ReadCommandFiltered
    lsls r3, #1
    strh r3, [r0, #0x1C]
    ldrh r2, [r0, #0x1E]
    muls r3, r2
    lsrs r3, #8
    strh r3, [r0, #0x20]
    bx r12
.size MusicEvent_Tempo,.-MusicEvent_Tempo

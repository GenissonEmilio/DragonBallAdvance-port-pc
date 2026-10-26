/* USA 0x0810ac7c: 20 complete bytes; separate from native C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_ModDepth
.type MusicEvent_ModDepth,%function
.thumb_func
MusicEvent_ModDepth:
    mov r12, lr
    bl Music_ReadCommandByte
    strb r3, [r1, #0x17]
    cmp r3, #0
    bne done
    bl Music_ClearModulation
done:
    bx r12
    .balign 4,0
.size MusicEvent_ModDepth,.-MusicEvent_ModDepth

/* USA 0x0810ac68: 20 complete bytes; separate from native C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_LfoSpeed
.type MusicEvent_LfoSpeed,%function
.thumb_func
MusicEvent_LfoSpeed:
    mov r12, lr
    bl Music_ReadCommandByte
    strb r3, [r1, #0x19]
    cmp r3, #0
    bne done
    bl Music_ClearModulation
done:
    bx r12
    .balign 4,0
.size MusicEvent_LfoSpeed,.-MusicEvent_LfoSpeed

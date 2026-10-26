/* USA 0x0810AC00..0x0810AC40: 64 complete bytes.
 * Exact GBA assembly; portable native C is validated separately. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_EndTie
.type MusicEvent_EndTie,%function
.thumb_func
MusicEvent_EndTie:
    push {r4, r5}
    ldr r2, [r1, #0x40]
    ldrb r3, [r2]
    cmp r3, #0x80
    bhs reuse_key
    strb r3, [r1, #5]
    adds r2, #1
    str r2, [r1, #0x40]
    b channel_list
reuse_key:
    ldrb r3, [r1, #5]
channel_list:
    ldr r1, [r1, #0x20]
    cmp r1, #0
    beq done
    movs r4, #0x83
    movs r5, #0x40
scan_channel:
    ldrb r2, [r1]
    tst r2, r4
    beq next_channel
    tst r2, r5
    bne next_channel
    ldrb r0, [r1, #0x11]
    cmp r0, r3
    bne next_channel
    movs r0, #0x40
    orrs r2, r0
    strb r2, [r1]
    b done
next_channel:
    ldr r1, [r1, #0x34]
    cmp r1, #0
    bne scan_channel
done:
    pop {r4, r5}
    bx lr
.size MusicEvent_EndTie,.-MusicEvent_EndTie

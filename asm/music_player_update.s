/* USA BDVE 0x0810A724..0x0810A98C, 616 bytes.
 * Assembly reconstruction, explicitly separate from the C port.
 * Includes the shared r3-call bridge and all literal/padding bytes.
 * No .incbin, instruction bytes, or post-assembly patches. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicPlayer_Update
.type MusicPlayer_Update,%function
.thumb_func
MusicPlayer_Update:
    ldr r2, lock_magic
    ldr r3, [r0, #0x34]
    cmp r2, r3
    beq lock_valid
    bx lr
lock_valid:
    adds r3, #1
    str r3, [r0, #0x34]
    push {r0, lr}
    ldr r3, [r0, #0x38]
    cmp r3, #0
    beq after_next_player
    ldr r0, [r0, #0x3c]
    bl _call_via_r3
after_next_player:
    pop {r0}
    push {r4, r5, r6, r7}
    mov r4, r8
    mov r5, sb
    mov r6, sl
    mov r7, fp
    push {r4, r5, r6, r7}
    adds r7, r0, #0
    ldr r0, [r7, #4]
    cmp r0, #0
    bge update_player
    b unlock
update_player:
    ldr r0, sound_pointer
    ldr r0, [r0]
    mov r8, r0
    adds r0, r7, #0
    bl Music_FadeOutBody
    ldr r0, [r7, #4]
    cmp r0, #0
    bge L_048
    b unlock
L_048:
    ldrh r0, [r7, #0x22]
    ldrh r1, [r7, #0x20]
    adds r0, r0, r1
    b tempo_compare
tempo_tick:
    ldrb r6, [r7, #8]
    ldr r5, [r7, #0x2c]
    movs r3, #1
    movs r4, #0
next_track:
    ldrb r0, [r5]
    movs r1, #0x80
    tst r1, r0
    bne L_062
    b L_174
L_062:
    mov sl, r3
    orrs r4, r3
    mov fp, r4
    ldr r4, [r5, #0x20]
    cmp r4, #0
    beq L_096
channel_gate:
    ldrb r1, [r4]
    movs r0, #0xc7
    tst r0, r1
    beq L_08A
    ldrb r0, [r4, #0x10]
    cmp r0, #0
    beq L_090
    subs r0, #1
    strb r0, [r4, #0x10]
    bne L_090
    movs r0, #0x40
    orrs r1, r0
    strb r1, [r4]
    b L_090
L_08A:
    adds r0, r4, #0
    bl Sound_ClearChannelChain
L_090:
    ldr r4, [r4, #0x34]
    cmp r4, #0
    bne channel_gate
L_096:
    ldrb r3, [r5]
    movs r0, #0x40
    tst r0, r3
    beq track_wait
    adds r0, r5, #0
    bl MusicPlayer_Clear
    movs r0, #0x80
    strb r0, [r5]
    movs r0, #2
    strb r0, [r5, #0xf]
    movs r0, #0x40
    strb r0, [r5, #0x13]
    movs r0, #0x16
    strb r0, [r5, #0x19]
    movs r0, #1
    adds r1, r5, #6
    strb r0, [r1, #0x1e]
    b track_wait
read_command:
    ldr r2, [r5, #0x40]
    ldrb r1, [r2]
    cmp r1, #0x80
    bhs L_0C8
    ldrb r1, [r5, #7]
    b L_0D2
L_0C8:
    adds r2, #1
    str r2, [r5, #0x40]
    cmp r1, #0xbd
    blo L_0D2
    strb r1, [r5, #7]
L_0D2:
    cmp r1, #0xcf
    blo L_0E8
    mov r0, r8
    ldr r3, [r0, #0x38]
    adds r0, r1, #0
    subs r0, #0xcf
    adds r1, r7, #0
    adds r2, r5, #0
    bl _call_via_r3
    b track_wait
L_0E8:
    cmp r1, #0xb0
    bls L_10A
    adds r0, r1, #0
    subs r0, #0xb1
    strb r0, [r7, #0xa]
    mov r3, r8
    ldr r3, [r3, #0x34]
    lsls r0, r0, #2
    ldr r3, [r3, r0]
    adds r0, r7, #0
    adds r1, r5, #0
    bl _call_via_r3
    ldrb r0, [r5]
    cmp r0, #0
    beq L_170
    b track_wait
L_10A:
    ldr r0, wait_table
    subs r1, #0x80
    adds r1, r1, r0
    ldrb r0, [r1]
    strb r0, [r5, #1]
track_wait:
    ldrb r0, [r5, #1]
    cmp r0, #0
    beq read_command
    subs r0, #1
    strb r0, [r5, #1]
    ldrb r1, [r5, #0x19]
    cmp r1, #0
    beq L_170
    ldrb r0, [r5, #0x17]
    cmp r0, #0
    beq L_170
    ldrb r0, [r5, #0x1c]
    cmp r0, #0
    beq L_136
    subs r0, #1
    strb r0, [r5, #0x1c]
    b L_170
L_136:
    ldrb r0, [r5, #0x1a]
    adds r0, r0, r1
    strb r0, [r5, #0x1a]
    adds r1, r0, #0
    subs r0, #0x40
    lsls r0, r0, #0x18
    bpl L_14A
    lsls r2, r1, #0x18
    asrs r2, r2, #0x18
    b L_14E
L_14A:
    movs r0, #0x80
    subs r2, r0, r1
L_14E:
    ldrb r0, [r5, #0x17]
    muls r0, r2, r0
    asrs r2, r0, #6
    ldrb r0, [r5, #0x16]
    eors r0, r2
    lsls r0, r0, #0x18
    beq L_170
    strb r2, [r5, #0x16]
    ldrb r0, [r5]
    ldrb r1, [r5, #0x18]
    cmp r1, #0
    bne L_16A
    movs r1, #0xc
    b L_16C
L_16A:
    movs r1, #3
L_16C:
    orrs r0, r1
    strb r0, [r5]
L_170:
    mov r3, sl
    mov r4, fp
L_174:
    subs r6, #1
    ble L_180
    movs r0, #0x50
    adds r5, r5, r0
    lsls r3, r3, #1
    b next_track
L_180:
    ldr r0, [r7, #0xc]
    adds r0, #1
    str r0, [r7, #0xc]
    cmp r4, #0
    bne L_192
    movs r0, #0x80
    lsls r0, r0, #0x18
    str r0, [r7, #4]
    b unlock
L_192:
    str r4, [r7, #4]
    ldrh r0, [r7, #0x22]
    subs r0, #0x96
tempo_compare:
    strh r0, [r7, #0x22]
    cmp r0, #0x96
    blo L_1A0
    b tempo_tick
L_1A0:
    ldrb r2, [r7, #8]
    ldr r5, [r7, #0x2c]
track_changes:
    ldrb r0, [r5]
    movs r1, #0x80
    tst r1, r0
    beq L_23E
    movs r1, #0xf
    tst r1, r0
    beq L_23E
    mov sb, r2
    adds r0, r7, #0
    adds r1, r5, #0
    bl MusicTrack_UpdateVolumePitch
    ldr r4, [r5, #0x20]
    cmp r4, #0
    beq L_234
channel_changes:
    ldrb r1, [r4]
    movs r0, #0xc7
    tst r0, r1
    bne L_1D2
    adds r0, r4, #0
    bl Sound_ClearChannelChain
    b L_22E
L_1D2:
    ldrb r0, [r4, #1]
    movs r6, #7
    ands r6, r0
    ldrb r3, [r5]
    movs r0, #3
    tst r0, r3
    beq L_1F0
    bl MusicChannel_UpdateVolume
    cmp r6, #0
    beq L_1F0
    ldrb r0, [r4, #0x1d]
    movs r1, #1
    orrs r0, r1
    strb r0, [r4, #0x1d]
L_1F0:
    ldrb r3, [r5]
    movs r0, #0xc
    tst r0, r3
    beq L_22E
    ldrb r1, [r4, #8]
    movs r0, #8
    ldrsb r0, [r5, r0]
    adds r2, r1, r0
    bpl L_204
    movs r2, #0
L_204:
    cmp r6, #0
    beq L_222
    mov r0, r8
    ldr r3, [r0, #0x30]
    adds r1, r2, #0
    ldrb r2, [r5, #9]
    adds r0, r6, #0
    bl _call_via_r3
    str r0, [r4, #0x20]
    ldrb r0, [r4, #0x1d]
    movs r1, #2
    orrs r0, r1
    strb r0, [r4, #0x1d]
    b L_22E
L_222:
    adds r1, r2, #0
    ldrb r2, [r5, #9]
    ldr r0, [r4, #0x24]
    bl Music_CalculateFrequency
    str r0, [r4, #0x20]
L_22E:
    ldr r4, [r4, #0x34]
    cmp r4, #0
    bne channel_changes
L_234:
    ldrb r0, [r5]
    movs r1, #0xf0
    ands r0, r1
    strb r0, [r5]
    mov r2, sb
L_23E:
    subs r2, #1
    ble unlock
    movs r0, #0x50
    adds r5, r5, r0
    bgt track_changes
unlock:
    ldr r0, lock_magic
    str r0, [r7, #0x34]
    pop {r0, r1, r2, r3, r4, r5, r6, r7}
    mov r8, r0
    mov sb, r1
    mov sl, r2
    mov fp, r3
    pop {r3}
.global _call_via_r3
.thumb_func
_call_via_r3:
    bx r3
.align 2,0
wait_table: .word gMusicWaitTable
sound_pointer: .word gSoundInfoPointer
lock_magic: .word 0x68736D53
.size MusicPlayer_Update,.-MusicPlayer_Update

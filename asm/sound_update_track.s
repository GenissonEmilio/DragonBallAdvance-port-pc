/* USA 0x0810AA00..0x0810AC00. Explicit assembly reference, separate
 * from native C. Includes both literals and zero alignment padding. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global Sound_UpdateTrack
.type Sound_UpdateTrack,%function
.thumb_func
Sound_UpdateTrack:
    push {r4, r5, r6, r7, lr}
    mov r4, r8
    mov r5, sb
    mov r6, sl
    mov r7, fp
    push {r4, r5, r6, r7}
    sub sp, #0x18
    str r1, [sp]
    adds r5, r2, #0
    ldr r1, sound_info_pointer
    ldr r1, [r1]
    str r1, [sp, #4]
    ldr r1, clock_table
    adds r0, r0, r1
    ldrb r0, [r0]
    strb r0, [r5, #4]
    ldr r3, [r5, #0x40]
    ldrb r0, [r3]
    cmp r0, #0x80
    bhs parameters_done
    strb r0, [r5, #5]
    adds r3, #1
    ldrb r0, [r3]
    cmp r0, #0x80
    bhs parameters_store
    strb r0, [r5, #6]
    adds r3, #1
    ldrb r0, [r3]
    cmp r0, #0x80
    bhs parameters_store
    ldrb r1, [r5, #4]
    adds r1, r1, r0
    strb r1, [r5, #4]
    adds r3, #1
parameters_store:
    str r3, [r5, #0x40]
parameters_done:
    movs r0, #0
    str r0, [sp, #0x14]
    adds r4, r5, #0
    adds r4, #0x24
    ldrb r2, [r4]
    movs r0, #0xc0
    tst r0, r2
    beq direct_tone
    ldrb r3, [r5, #5]
    movs r0, #0x40
    tst r0, r2
    beq unsplit_key
    ldr r1, [r5, #0x2c]
    adds r1, r1, r3
    ldrb r0, [r1]
    b voice_index
unsplit_key:
    adds r0, r3, #0
voice_index:
    lsls r1, r0, #1
    adds r1, r1, r0
    lsls r1, r1, #2
    ldr r0, [r5, #0x28]
    adds r1, r1, r0
    mov sb, r1
    mov r6, sb
    ldrb r1, [r6]
    movs r0, #0xc0
    tst r0, r1
    beq voice_valid
    b done
voice_valid:
    movs r0, #0x80
    tst r0, r2
    beq priority
    ldrb r1, [r6, #3]
    movs r0, #0x80
    tst r0, r1
    beq rhythm_key
    subs r1, #0xc0
    lsls r1, r1, #1
    str r1, [sp, #0x14]
rhythm_key:
    ldrb r3, [r6, #1]
    b priority
direct_tone:
    mov sb, r4
    ldrb r3, [r5, #5]
priority:
    str r3, [sp, #8]
    ldr r6, [sp]
    ldrb r1, [r6, #9]
    ldrb r0, [r5, #0x1d]
    adds r0, r0, r1
    cmp r0, #0xff
    bls priority_ready
    movs r0, #0xff
priority_ready:
    str r0, [sp, #0x10]
    mov r6, sb
    ldrb r0, [r6]
    movs r6, #7
    ands r6, r0
    str r6, [sp, #0xc]
    beq pcm_select
    ldr r0, [sp, #4]
    ldr r4, [r0, #0x1c]
    cmp r4, #0
    bne cgb_available
    b done
cgb_available:
    subs r6, #1
    lsls r0, r6, #6
    adds r4, r4, r0
    ldrb r1, [r4]
    movs r0, #0xc7
    tst r0, r1
    beq activate
    movs r0, #0x40
    tst r0, r1
    bne activate
    ldrb r1, [r4, #0x13]
    ldr r0, [sp, #0x10]
    cmp r1, r0
    blo activate
    beq cgb_tie
    b done
cgb_tie:
    ldr r0, [r4, #0x2c]
    cmp r0, r5
    bhs activate
    b done
pcm_select:
    ldr r6, [sp, #0x10]
    adds r7, r5, #0
    movs r2, #0
    mov r8, r2
    ldr r4, [sp, #4]
    ldrb r3, [r4, #6]
    adds r4, #0x50
pcm_loop:
    ldrb r1, [r4]
    movs r0, #0xc7
    tst r0, r1
    beq activate
    movs r0, #0x40
    tst r0, r1
    beq pcm_active
    cmp r2, #0
    bne pcm_compare
    adds r2, #1
    ldrb r6, [r4, #0x13]
    ldr r7, [r4, #0x2c]
    b pcm_remember
pcm_active:
    cmp r2, #0
    bne pcm_next
pcm_compare:
    ldrb r0, [r4, #0x13]
    cmp r0, r6
    bhs pcm_priority_tie
    adds r6, r0, #0
    ldr r7, [r4, #0x2c]
    b pcm_remember
pcm_priority_tie:
    bhi pcm_next
    ldr r0, [r4, #0x2c]
    cmp r0, r7
    bls pcm_owner_tie
    adds r7, r0, #0
    b pcm_remember
pcm_owner_tie:
    blo pcm_next
pcm_remember:
    mov r8, r4
pcm_next:
    adds r4, #0x40
    subs r3, #1
    bgt pcm_loop
    mov r4, r8
    cmp r4, #0
    beq done
activate:
    adds r0, r4, #0
    bl Sound_ClearChannelChain
    movs r1, #0
    str r1, [r4, #0x30]
    ldr r3, [r5, #0x20]
    str r3, [r4, #0x34]
    cmp r3, #0
    beq link_head
    str r4, [r3, #0x30]
link_head:
    str r4, [r5, #0x20]
    str r5, [r4, #0x2c]
    ldrb r0, [r5, #0x1b]
    strb r0, [r5, #0x1c]
    cmp r0, r1
    beq volume_pitch
    adds r1, r5, #0
    bl Music_ClearModulation
volume_pitch:
    ldr r0, [sp]
    adds r1, r5, #0
    bl MusicTrack_UpdateVolumePitch
    ldr r0, [r5, #4]
    str r0, [r4, #0x10]
    ldr r0, [sp, #0x10]
    strb r0, [r4, #0x13]
    ldr r0, [sp, #8]
    strb r0, [r4, #8]
    ldr r0, [sp, #0x14]
    strb r0, [r4, #0x14]
    mov r6, sb
    ldrb r0, [r6]
    strb r0, [r4, #1]
    ldr r7, [r6, #4]
    str r7, [r4, #0x24]
    ldr r0, [r6, #8]
    str r0, [r4, #4]
    ldrh r0, [r5, #0x1e]
    strh r0, [r4, #0xc]
    bl MusicChannel_UpdateVolume
    ldrb r1, [r4, #8]
    movs r0, #8
    ldrsb r0, [r5, r0]
    adds r3, r1, r0
    bpl key_ready
    movs r3, #0
key_ready:
    ldr r6, [sp, #0xc]
    cmp r6, #0
    beq pcm_frequency
    mov r6, sb
    ldrb r0, [r6, #2]
    strb r0, [r4, #0x1e]
    ldrb r1, [r6, #3]
    movs r0, #0x80
    tst r0, r1
    bne default_sweep
    movs r0, #0x70
    tst r0, r1
    bne sweep_ready
default_sweep:
    movs r1, #8
sweep_ready:
    strb r1, [r4, #0x1f]
    ldrb r2, [r5, #9]
    adds r1, r3, #0
    ldr r0, [sp, #0xc]
    ldr r3, [sp, #4]
    ldr r3, [r3, #0x30]
    bl _call_via_r3
    b frequency_ready
pcm_frequency:
    ldrb r2, [r5, #9]
    adds r1, r3, #0
    adds r0, r7, #0
    bl Music_CalculateFrequency
frequency_ready:
    str r0, [r4, #0x20]
    movs r0, #0x80
    strb r0, [r4]
    ldrb r1, [r5]
    movs r0, #0xf0
    ands r0, r1
    strb r0, [r5]
done:
    add sp, #0x18
    pop {r0, r1, r2, r3, r4, r5, r6, r7}
    mov r8, r0
    mov sb, r1
    mov sl, r2
    mov fp, r3
    pop {r0}
    bx r0
.balign 4,0
sound_info_pointer: .word gSoundInfoPointer
clock_table: .word gMusicWaitTable
.size Sound_UpdateTrack,.-Sound_UpdateTrack

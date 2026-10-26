/* USA BDVE 0x0810A084..0x0810A4AC, full mixed Thumb/ARM mixer.
 * Assembly reproduction, separate from the semantic C port; never counts as C.
 * Adapted from cached SAT-R/sa2 m4a0.s, revision
 * 393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d, with USA addresses.
 * Includes all literal and alignment bytes; no raw instruction arrays. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.balign 4,0
.equ SOUND_INFO_PTR,0x3007FF0
.equ ID_NUMBER,0x68736D53
.equ SoundMainRAM_Buffer,0x30008B0
.equ REG_VCOUNT,0x4000006
.equ VCOUNT_VBLANK,0xA0
.equ TOTAL_SCANLINES,0xE4
.equ PCM_DMA_BUF_SIZE,0x630
.equ SOUND_CHANNEL_SF_ON,0xC7
.equ SOUND_CHANNEL_SF_START,0x80
.equ SOUND_CHANNEL_SF_STOP,0x40
.equ SOUND_CHANNEL_SF_ENV_ATTACK,0x3
.equ SOUND_CHANNEL_SF_LOOP,0x10
.equ SOUND_CHANNEL_SF_IEC,0x4
.equ SOUND_CHANNEL_SF_ENV,0x3
.equ SOUND_CHANNEL_SF_ENV_DECAY,0x2
.equ WAVE_DATA_FLAG_LOOP,0xC0
.equ o_SoundInfo_ident,0x0
.equ o_SoundInfo_pcmDmaCounter,0x4
.equ o_SoundInfo_reverb,0x5
.equ o_SoundInfo_maxChans,0x6
.equ o_SoundInfo_maxLines,0xC
.equ o_SoundInfo_MPlayMainHead,0x20
.equ o_SoundInfo_musicPlayerHead,0x24
.equ o_SoundInfo_CgbSound,0x28
.equ o_SoundInfo_pcmSamplesPerVBlank,0x10
.equ o_SoundInfo_pcmDmaPeriod,0xB
.equ o_SoundInfo_pcmBuffer,0x350
.equ o_SoundInfo_divFreq,0x18
.equ o_SoundInfo_chans,0x50
.equ o_SoundChannel_statusFlags,0x0
.equ o_SoundChannel_type,0x1
.equ o_SoundChannel_rightVolume,0x2
.equ o_SoundChannel_leftVolume,0x3
.equ o_SoundChannel_attack,0x4
.equ o_SoundChannel_decay,0x5
.equ o_SoundChannel_sustain,0x6
.equ o_SoundChannel_release,0x7
.equ o_SoundChannel_envelopeVolume,0x9
.equ o_SoundChannel_envelopeVolumeRight,0xA
.equ o_SoundChannel_envelopeVolumeLeft,0xB
.equ o_SoundChannel_pseudoEchoVolume,0xC
.equ o_SoundChannel_pseudoEchoLength,0xD
.equ o_SoundChannel_count,0x18
.equ o_SoundChannel_fw,0x1C
.equ o_SoundChannel_frequency,0x20
.equ o_SoundChannel_wav,0x24
.equ o_SoundChannel_currentPointer,0x28
.equ SoundChannel_size,0x40
.equ o_WaveData_data,0x10
.equ o_WaveData_size,0xC
.equ o_WaveData_flags,0x3
.equ o_WaveData_loopStart,0x8
.global Func_0810A084
.type Func_0810A084,%function
.thumb_func
Func_0810A084:
	ldr r0, lt_SOUND_INFO_PTR
	ldr r0, [r0]
	ldr r2, lt_ID_NUMBER
	ldr r3, [r0, o_SoundInfo_ident]
	cmp r2, r3
	beq SoundMain_1
	bx lr @ Exit the function if ident does not match ID_NUMBER.
SoundMain_1:
	adds r3, 1
	str r3, [r0, o_SoundInfo_ident]
	push {r4-r7,lr}
	mov r1, r8
	mov r2, r9
	mov r3, r10
	mov r4, r11
	push {r0-r4}
	sub sp, 0x18
	ldrb r1, [r0, o_SoundInfo_maxLines]
	cmp r1, 0 @ if maxLines is 0, there is no maximum
	beq SoundMain_3
	ldr r2, lt_REG_VCOUNT
	ldrb r2, [r2]
	cmp r2, VCOUNT_VBLANK
	bhs SoundMain_2
	adds r2, TOTAL_SCANLINES
SoundMain_2:
	adds r1, r2
SoundMain_3:
	str r1, [sp, 0x14]
	ldr r3, [r0, o_SoundInfo_MPlayMainHead]
	cmp r3, 0
	beq SoundMain_4
	ldr r0, [r0, o_SoundInfo_musicPlayerHead]
	bl SoundMain_CallViaR3
	ldr r0, [sp, 0x18]
SoundMain_4:
	ldr r3, [r0, o_SoundInfo_CgbSound]
	bl SoundMain_CallViaR3
	ldr r0, [sp, 0x18]
	ldr r3, [r0, o_SoundInfo_pcmSamplesPerVBlank]
	mov r8, r3
	ldr r5, lt_o_SoundInfo_pcmBuffer
	adds r5, r0
	ldrb r4, [r0, o_SoundInfo_pcmDmaCounter]
	subs r7, r4, 1
	bls SoundMain_5
	ldrb r1, [r0, o_SoundInfo_pcmDmaPeriod]
	subs r1, r7
	mov r2, r8
	muls r2, r1
	adds r5, r2
SoundMain_5:
	str r5, [sp, 0x8]
	ldr r6, lt_PCM_DMA_BUF_SIZE
	ldr r3, lt_SoundMainRAM_Buffer
	bx r3

	.align 2, 0
lt_SOUND_INFO_PTR:        .word SOUND_INFO_PTR
lt_ID_NUMBER:             .word ID_NUMBER
lt_SoundMainRAM_Buffer:   .word SoundMainRAM_Buffer + 1
lt_REG_VCOUNT:            .word REG_VCOUNT
lt_o_SoundInfo_pcmBuffer: .word o_SoundInfo_pcmBuffer
lt_PCM_DMA_BUF_SIZE:      .word PCM_DMA_BUF_SIZE
.size Func_0810A084,.-Func_0810A084
.global SoundMainRam
.type SoundMainRam,%function
.thumb_func
SoundMainRam:
	ldrb r3, [r0, o_SoundInfo_reverb]
	cmp r3, 0
	beq SoundMainRAM_NoReverb
	adr r1, SoundMainRAM_Reverb
	bx r1
	.arm
SoundMainRAM_Reverb:
	cmp r4, 0x2
	addeq r7, r0, o_SoundInfo_pcmBuffer
	addne r7, r5, r8
	mov r4, r8
_081DCEC4:
	ldrsb r0, [r5, r6]
	ldrsb r1, [r5]
	add r0, r0, r1
	ldrsb r1, [r7, r6]
	add r0, r0, r1
	ldrsb r1, [r7], 0x1
	add r0, r0, r1
	mul r1, r0, r3
	mov r0, r1, asr 9
	tst r0, 0x80
	addne r0, r0, 0x1
	strb r0, [r5, r6]
	strb r0, [r5], 0x1
	subs r4, r4, 0x1
	bgt _081DCEC4
	adr r0, _081DCF36 + 1 @ plus 1 because THUMB
	bx r0
	.thumb
SoundMainRAM_NoReverb:
	movs r0, 0
	mov r1, r8
	adds r6, r5
	lsrs r1, 3
	bcc SoundMainRAM_NoReverb_Ok
	stm r5!, {r0}
	stm r6!, {r0}
SoundMainRAM_NoReverb_Ok:
	lsrs r1, 1
	bcc SoundMainRAM_NoReverb_Loop
	stm r5!, {r0}
	stm r6!, {r0}
	stm r5!, {r0}
	stm r6!, {r0}
SoundMainRAM_NoReverb_Loop:
	stm r5!, {r0}
	stm r6!, {r0}
	stm r5!, {r0}
	stm r6!, {r0}
	stm r5!, {r0}
	stm r6!, {r0}
	stm r5!, {r0}
	stm r6!, {r0}
	subs r1, 1
	bgt SoundMainRAM_NoReverb_Loop
_081DCF36:
	ldr r4, [sp, 0x18]
	ldr r0, [r4, o_SoundInfo_divFreq]
	mov r12, r0
	ldrb r0, [r4, o_SoundInfo_maxChans]
	adds r4, o_SoundInfo_chans

SoundMainRAM_ChanLoop:
	str r0, [sp, 0x4]
	ldr r3, [r4, o_SoundChannel_wav]
	ldr r0, [sp, 0x14]
	cmp r0, 0
	beq _081DCF60
	ldr r1, =REG_VCOUNT
	ldrb r1, [r1]
	cmp r1, VCOUNT_VBLANK
	bhs _081DCF54
	adds r1, TOTAL_SCANLINES
_081DCF54:
	cmp r1, r0
	blo _081DCF60
	b _081DD24A

	.pool

_081DCF60:
	ldrb r6, [r4, o_SoundChannel_statusFlags]
	movs r0, SOUND_CHANNEL_SF_ON
	tst r0, r6
	bne _081DCF6A
	b _081DD240
_081DCF6A:
	movs r0, SOUND_CHANNEL_SF_START
	tst r0, r6
	beq _081DCFA0
	movs r0, SOUND_CHANNEL_SF_STOP
	tst r0, r6
	bne _081DCFB0
	movs r6, SOUND_CHANNEL_SF_ENV_ATTACK
	strb r6, [r4, o_SoundChannel_statusFlags]
	adds r0, r3, 0
	adds r0, o_WaveData_data
	str r0, [r4, o_SoundChannel_currentPointer]
	ldr r0, [r3, o_WaveData_size]
	str r0, [r4, o_SoundChannel_count]
	movs r5, 0
	strb r5, [r4, o_SoundChannel_envelopeVolume]
	str r5, [r4, o_SoundChannel_fw]
	ldrb r2, [r3, o_WaveData_flags]
	movs r0, WAVE_DATA_FLAG_LOOP
	tst r0, r2
	beq _081DCFF8
	movs r0, SOUND_CHANNEL_SF_LOOP
	orrs r6, r0
	strb r6, [r4, o_SoundChannel_statusFlags]
	b _081DCFF8
_081DCFA0:
	ldrb r5, [r4, o_SoundChannel_envelopeVolume]
	movs r0, SOUND_CHANNEL_SF_IEC
	tst r0, r6
	beq _081DCFB6
	ldrb r0, [r4, o_SoundChannel_pseudoEchoLength]
	subs r0, 1
	strb r0, [r4, o_SoundChannel_pseudoEchoLength]
	bhi _081DD006
_081DCFB0:
	movs r0, 0
	strb r0, [r4, o_SoundChannel_statusFlags]
	b _081DD240
_081DCFB6:
	movs r0, SOUND_CHANNEL_SF_STOP
	tst r0, r6
	beq _081DCFD6
	ldrb r0, [r4, o_SoundChannel_release]
	muls r5, r0
	lsrs r5, 8
	ldrb r0, [r4, o_SoundChannel_pseudoEchoVolume]
	cmp r5, r0
	bhi _081DD006
_081DCFC8:
	ldrb r5, [r4, o_SoundChannel_pseudoEchoVolume]
	cmp r5, 0
	beq _081DCFB0
	movs r0, SOUND_CHANNEL_SF_IEC
	orrs r6, r0
	strb r6, [r4, o_SoundChannel_statusFlags]
	b _081DD006
_081DCFD6:
	movs r2, SOUND_CHANNEL_SF_ENV
	ands r2, r6
	cmp r2, SOUND_CHANNEL_SF_ENV_DECAY
	bne _081DCFF4
	ldrb r0, [r4, o_SoundChannel_decay]
	muls r5, r0
	lsrs r5, 8
	ldrb r0, [r4, o_SoundChannel_sustain]
	cmp r5, r0
	bhi _081DD006
	adds r5, r0, 0
	beq _081DCFC8
	subs r6, 0x1
	strb r6, [r4, o_SoundChannel_statusFlags]
	b _081DD006
_081DCFF4:
	cmp r2, SOUND_CHANNEL_SF_ENV_ATTACK
	bne _081DD006
_081DCFF8:
	ldrb r0, [r4, o_SoundChannel_attack]
	adds r5, r0
	cmp r5, 0xFF
	bcc _081DD006
	movs r5, 0xFF
	subs r6, 0x1
	strb r6, [r4, o_SoundChannel_statusFlags]
_081DD006:
	strb r5, [r4, o_SoundChannel_envelopeVolume]
	ldr r0, [sp, 0x18]
	ldrb r0, [r0, o_SoundChannel_release]
	adds r0, 0x1
	muls r0, r5
	lsrs r5, r0, 4
	ldrb r0, [r4, o_SoundChannel_rightVolume]
	muls r0, r5
	lsrs r0, 8
	strb r0, [r4, o_SoundChannel_envelopeVolumeRight]
	ldrb r0, [r4, o_SoundChannel_leftVolume]
	muls r0, r5
	lsrs r0, 8
	strb r0, [r4, o_SoundChannel_envelopeVolumeLeft]
	movs r0, SOUND_CHANNEL_SF_LOOP
	ands r0, r6
	str r0, [sp, 0x10]
	beq _081DD03A
	adds r0, r3, 0
	adds r0, o_WaveData_data
	ldr r1, [r3, o_WaveData_loopStart]
	adds r0, r1
	str r0, [sp, 0xC]
	ldr r0, [r3, o_WaveData_size]
	subs r0, r1
	str r0, [sp, 0x10]
_081DD03A:
	ldr r5, [sp, 0x8]
	ldr r2, [r4, o_SoundChannel_count]
	ldr r3, [r4, o_SoundChannel_currentPointer]
	adr r0, _081DD044
	bx r0
	.arm
_081DD044:
	str r8, [sp]
	ldrb r10, [r4, o_SoundChannel_envelopeVolumeRight]
	ldrb r11, [r4, o_SoundChannel_envelopeVolumeLeft]
	lsl sl, sl, #0x10
	lsl fp, fp, #0x10
	ldrb r0, [r4, o_SoundChannel_type]
	tst r0, 0x8
	beq _081DD19C
_081DD07C:
	cmp r2, 0x4
	ble _081DD0EC
	subs r2, r2, r8
	movgt lr, 0
	bgt _081DD0A8
	mov lr, r8
	add r2, r2, r8
	sub r8, r2, 0x4
	sub lr, lr, r8
	ands r2, r2, 0x3
	moveq r2, 0x4
_081DD0A8:
	ldr r6, [r5]
	ldr r7, [r5, PCM_DMA_BUF_SIZE]
_081DD0B0:
	ldrsb r0, [r3], 0x1
	mul r1, r10, r0
	bic r1, r1, 0xFF0000
	add r6, r1, r6, ror 8
	mul r1, r11, r0
	bic r1, r1, 0xFF0000
	add r7, r1, r7, ror 8
	adds r5, r5, 0x40000000
	bcc _081DD0B0
	str r7, [r5, PCM_DMA_BUF_SIZE]
	str r6, [r5], 0x4
	subs r8, r8, 0x4
	bgt _081DD0A8
	adds r8, r8, lr
	beq _081DD22C
_081DD0EC:
	ldr r6, [r5]
	ldr r7, [r5, PCM_DMA_BUF_SIZE]
_081DD0F4:
	ldrsb r0, [r3], 0x1
	mul r1, r10, r0
	bic r1, r1, 0xFF0000
	add r6, r1, r6, ror 8
	mul r1, r11, r0
	bic r1, r1, 0xFF0000
	add r7, r1, r7, ror 8
	subs r2, r2, 0x1
	beq _081DD164
_081DD118:
	adds r5, r5, 0x40000000
	bcc _081DD0F4
	str r7, [r5, PCM_DMA_BUF_SIZE]
	str r6, [r5], 0x4
	subs r8, r8, 0x4
	bgt _081DD07C
	b _081DD22C
_081DD134:
	ldr r0, [sp, 0x18]
	cmp r0, 0
	beq _081DD158
	ldr r3, [sp, 0x14]
	rsb sb, r2, 0
_081DD148:
	adds r2, r0, r2
	bgt _081DD1FC
	sub sb, sb, r0
	b _081DD148
_081DD158:
	pop {r4,r12}
	mov r2, 0
	b _081DD174
_081DD164:
	ldr r2, [sp, 0x10]
	cmp r2, 0
	ldrne r3, [sp, 0xC]
	bne _081DD118
_081DD174:
	strb r2, [r4, o_SoundChannel_statusFlags]
	mov r0, r5, lsr 30
	bic r5, r5, 0xC0000000
	rsb r0, r0, 0x3
	mov r0, r0, lsl 3
	mov r6, r6, ror r0
	mov r7, r7, ror r0
	str r7, [r5, PCM_DMA_BUF_SIZE]
	str r6, [r5], 0x4
	b _081DD234
_081DD19C:
	push {r4,r12}
	ldr lr, [r4, #0x1c]
	ldr r1, [r4, o_SoundChannel_frequency]
	mul r4, r12, r1
	ldrsb r0, [r3]
	ldrsb r1, [r3, 0x1]!
	sub r1, r1, r0
_081DD1B4:
	ldr r6, [r5]
	ldr r7, [r5, PCM_DMA_BUF_SIZE]
_081DD1BC:
	mul sb, lr, r1
	add sb, r0, sb, asr 23
	mul r12, r10, sb
	bic r12, r12, 0xFF0000
	add r6, r12, r6, ror 8
	mul r12, r11, sb
	bic r12, r12, 0xFF0000
	add r7, r12, r7, ror 8
	add lr, lr, r4
	lsrs sb, lr, 23
	beq _081DD208
	bic lr, lr, 0x3F800000
	subs r2, r2, sb
	ble _081DD134
	subs sb, sb, 0x1
	addeq r0, r0, r1
_081DD1FC:
	ldrsbne r0, [r3, sb]!
	ldrsb r1, [r3, 0x1]!
	sub r1, r1, r0
_081DD208:
	adds r5, r5, 0x40000000
	bcc _081DD1BC
	str r7, [r5, PCM_DMA_BUF_SIZE]
	str r6, [r5], 0x4
	subs r8, r8, 0x4
	bgt _081DD1B4
	sub r3, r3, 0x1
	pop {r4,r12}
	str lr, [r4, o_SoundChannel_fw]
_081DD22C:
	str r2, [r4, o_SoundChannel_count]
	str r3, [r4, o_SoundChannel_currentPointer]
_081DD234:
	ldr r8, [sp]
	add r0, pc, 0x1
	bx r0
	.thumb
_081DD240:
	ldr r0, [sp, 0x4]
	subs r0, 1
	ble _081DD24A
	adds r4, SoundChannel_size
	b SoundMainRAM_ChanLoop
_081DD24A:
	ldr r0, [sp, 0x18]
	ldr r3, =ID_NUMBER
	str r3, [r0]
	add sp, 0x1C
	pop {r0-r7}
	mov r8, r0
	mov r9, r1
	mov r10, r2
	mov r11, r3
	pop {r3}
SoundMain_CallViaR3:
	bx r3
	.pool
.size SoundMainRam,.-SoundMainRam

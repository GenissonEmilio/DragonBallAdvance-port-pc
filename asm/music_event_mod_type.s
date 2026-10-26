/* USA 0x0810A694: SDK assembly; counted separately from matching C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_ModType
.type MusicEvent_ModType,%function
.thumb_func
MusicEvent_ModType:
    mov r12, lr
    bl Music_ReadCommandFiltered
    ldrb r0, [r1, #0x18]
    cmp r0, r3
    beq .Lreturn
    strb r3, [r1, #0x18]
    ldrb r3, [r1]
    movs r2, #0x0F
    orrs r3, r2
    strb r3, [r1]
.Lreturn:
    bx r12
.size MusicEvent_ModType,.-MusicEvent_ModType

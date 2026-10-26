/* USA 0x0810A6C0: SDK assembly; counted separately from matching C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global MusicEvent_Port
.type MusicEvent_Port,%function
.thumb_func
MusicEvent_Port:
    mov r12, lr
    ldr r2, [r1, #0x40]
    ldrb r3, [r2]
    adds r2, #1
    ldr r0, port_base
    adds r0, r0, r3
    bl Music_ReadCommandFilteredFromPointer
    strb r3, [r0]
    bx r12
port_base: .word 0x04000060
.size MusicEvent_Port,.-MusicEvent_Port

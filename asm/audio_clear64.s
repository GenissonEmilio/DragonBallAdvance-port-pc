/* USA 0810A4AC..0810A4C4: clear exactly 64 bytes, including original ABI. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global Audio_Clear64
.type Audio_Clear64,%function
.thumb_func
Audio_Clear64:
    mov r12, r4
    movs r1, #0
    movs r2, #0
    movs r3, #0
    movs r4, #0
    stmia r0!, {r1,r2,r3,r4}
    stmia r0!, {r1,r2,r3,r4}
    stmia r0!, {r1,r2,r3,r4}
    stmia r0!, {r1,r2,r3,r4}
    mov r4, r12
    bx lr
.align 2,0
.size Audio_Clear64,.-Audio_Clear64

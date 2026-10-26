/* USA: explicit SDK assembly, excluded from C matching counts. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global Music_ReadCommandFiltered
.type Music_ReadCommandFiltered,%function
.thumb_func
Music_ReadCommandFiltered:
    ldr r2, [r1, #0x40]
    adds r3, r2, #1
    str r3, [r1, #0x40]
    ldrb r3, [r2]
    b Sound_FilterAddress
    .balign 4,0
.size Music_ReadCommandFiltered,.-Music_ReadCommandFiltered

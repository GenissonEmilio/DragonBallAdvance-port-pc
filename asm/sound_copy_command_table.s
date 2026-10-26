/* USA 0810A514..0810A548. Copy, filtered-byte entry, address checker,
 * shared source-address literal, and all alignment bytes. Assembly, not C. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2,0
.global Sound_CopyCommandTable
.type Sound_CopyCommandTable,%function
.thumb_func
Sound_CopyCommandTable:
    mov r12, lr
    movs r1, #36
    ldr r2, command_template
copy_next:
    ldr r3, [r2]
    bl Sound_FilterAddress
    stmia r0!, {r3}
    adds r2, #4
    subs r1, #1
    bgt copy_next
    bx r12
.align 2,0
.global Sound_ReadByteFiltered
.thumb_func
Sound_ReadByteFiltered:
    ldrb r3, [r2]
.global Sound_FilterAddress
.thumb_func
Sound_FilterAddress:
    push {r0}
    lsrs r0, r2, #25
    bne address_done
    ldr r0, command_template
    cmp r2, r0
    blo address_reject
    lsrs r0, r2, #14
    beq address_done
address_reject:
    movs r3, #0
address_done:
    pop {r0}
    bx lr
.align 2,0
command_template: .word gSoundCommandTemplate
.size Sound_CopyCommandTable,.-Sound_CopyCommandTable

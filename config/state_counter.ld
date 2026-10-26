OUTPUT_FORMAT("elf32-littlearm")
OUTPUT_ARCH(arm)
ENTRY(State_IncrementWord10IfFlag22)

gDbaaGameState = 0x02029F30;

SECTIONS
{
    .text 0x0800144C : { *(.text) *(.text.*) }
    /DISCARD/ : { *(.comment) *(.note*) *(.ARM.attributes) }
}

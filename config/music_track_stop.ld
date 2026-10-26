OUTPUT_FORMAT("elf32-littlearm")
OUTPUT_ARCH(arm)
ENTRY(MusicTrack_Stop)
gSoundInfoPointer = 0x03007FF0;
PHDRS { code PT_LOAD FLAGS(5); }
SECTIONS {
    .text 0x0810A98C : {
        FILL(0);
        *(.text) *(.data)
        . = ALIGN(4);
    } :code
    /DISCARD/ : { *(.comment) *(.note*) *(.ARM.attributes) }
}

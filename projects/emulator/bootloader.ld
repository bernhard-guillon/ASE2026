/* Bootloader Linker Script for RISC-V Neural Network Emulator
 *
 * Memory Layout:
 * 0x00000000 - 0x0000FFFF (64 KB):  Bootloader code (.text)
 * 0x00010000 - 0x000FFFFF (960 KB): Bootloader data (.data, .rodata, embedded models)
 * 0x00100000 - 0x1FFFFFFF:          Application memory (for future use)
 *
 * Model Placement (by bootloader):
 * - Generator model:   0x10000 - 0xF3C7F (loaded at runtime)
 * - Stack:             0x20000 (initialized in bootloader)
 *
 * Notes:
 * - The bootloader loads embedded model data from .data to runtime addresses
 * - Models are NOT linked to their final addresses; they're loaded at boot
 * - Verify the bootloader.ld placement matches model_compiler.py expectations
 */

MEMORY
{
    /* Bootloader code space - where executable instructions live */
    CODE (rx) : ORIGIN = 0x00000000, LENGTH = 64K

    /* Bootloader data space - embedded model binaries and static data */
    DATA (rw) : ORIGIN = 0x00010000, LENGTH = 960K
}

SECTIONS
{
    /* Executable code section - placed at start of memory */
    .text :
    {
        *(.text)
        *(.text.*)
    } > CODE

    /* Read-only data section (embedded models, constants) */
    .rodata :
    {
        *(.rodata)
        *(.rodata.*)
    } > DATA

    /* Initialized data section */
    .data :
    {
        *(.data)
        *(.data.*)
    } > DATA

    /* Uninitialized data section */
    .bss :
    {
        *(.bss)
        *(.bss.*)
        *(COMMON)
    } > DATA

    /* Discard unneeded sections */
    /DISCARD/ : { *(.note.GNU-stack) *(.gnu_eh_frame) *(.eh_frame_hdr) }
}

/* Entry point for bootloader */
ENTRY(_start)

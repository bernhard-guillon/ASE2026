ENTRY(_start)

MEMORY {
    RAM (xrw) : ORIGIN = 0x0, LENGTH = 64K
}

SECTIONS {
    .text : {
        *(.text .text.*)
    } > RAM

    .rodata : {
        *(.rodata .rodata.*)
    } > RAM

    .data : {
        *(.data .data.*)
    } > RAM

    .bss : {
        *(.bss .bss.*)
    } > RAM
}

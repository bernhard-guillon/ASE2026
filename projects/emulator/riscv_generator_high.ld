/* Linker script for RISC-V generator model (high data)
   Places code at 0x0 and model data at 0x30000 to avoid framebuffer (0x20000).
*/

MEMORY
{
  mem : ORIGIN = 0x00000000, LENGTH = 256M
}

SECTIONS
{
  . = 0x00000000;
  .text : { *(.text) }
  . = ALIGN(4);

  . = 0x00030000;
  .model : { *(.model) }
  . = ALIGN(4);
  .rodata : { *(.rodata) }
  . = ALIGN(4);
  .data : { *(.data) }
  . = ALIGN(4);
  .bss : { *(.bss) }
}

/* Flat memory linker script for RISC-V
   Everything at address 0, suitable for bare-metal
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
  .rodata : { *(.rodata) }
  . = ALIGN(4);
  .data : { *(.data) }
  . = ALIGN(4);
  .bss : { *(.bss) }
}

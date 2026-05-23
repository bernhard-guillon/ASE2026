/* Linker script for RISC-V generator model
   Places code at 0x0 and data at 0x10000
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
  
  . = 0x00010000;
  .rodata : { *(.rodata) }
  . = ALIGN(4);
  .data : { *(.data) }
  . = ALIGN(4);
  .bss : { *(.bss) }
}

/* Linker script for RISC-V neural network models
   Places code at 0x0 and data at appropriate addresses
*/

MEMORY
{
  rom (rx) : ORIGIN = 0x00010000, LENGTH = 32M
  ram (rwx) : ORIGIN = 0x00000000, LENGTH = 32M
}

SECTIONS
{
  . = 0x00010000;
  .text : { *(.text) }
  
  . = 0x00011000;
  .rodata : { *(.rodata) }
  
  . = 0x00150000;
  .data : { *(.data) }
  
  . = ALIGN(4);
  .bss : { *(.bss) }
}

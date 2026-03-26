file(REMOVE_RECURSE
  "CMakeFiles/elf_loader_tests"
  "elf_loader_tests/test_array_index.elf"
  "elf_loader_tests/test_array_index.o"
  "elf_loader_tests/test_const_fb.elf"
  "elf_loader_tests/test_const_fb.o"
  "elf_loader_tests/test_const_pattern.elf"
  "elf_loader_tests/test_const_pattern.o"
  "elf_loader_tests/test_nop_loop.elf"
  "elf_loader_tests/test_nop_loop.o"
  "elf_loader_tests/test_read_offset.elf"
  "elf_loader_tests/test_read_offset.o"
  "elf_loader_tests/test_rodata_read.elf"
  "elf_loader_tests/test_rodata_read.o"
  "elf_loader_tests/test_write_immediately.elf"
  "elf_loader_tests/test_write_immediately.o"
)

# Per-language clean rules from dependency scanning.
foreach(lang )
  include(CMakeFiles/elf_loader_tests.dir/cmake_clean_${lang}.cmake OPTIONAL)
endforeach()

# CMake generated Testfile for 
# Source directory: /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator/hdl
# Build directory: /home/nice/Uni/Master/ASE2026/ASE2026/emulator_build/hdl
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(verilator/asm/basic_hello "/home/nice/Uni/Master/ASE2026/ASE2026/emulator_build/verilator_runner" "/home/nice/Uni/Master/ASE2026/ASE2026/emulator_build/blackbox_tests/asm/basic/hello/test.elf" "--cycles" "50000")
set_tests_properties(verilator/asm/basic_hello PROPERTIES  TIMEOUT "10" WORKING_DIRECTORY "/home/nice/Uni/Master/ASE2026/ASE2026/emulator_build" _BACKTRACE_TRIPLES "/home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator/hdl/CMakeLists.txt;70;add_test;/home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator/hdl/CMakeLists.txt;0;")

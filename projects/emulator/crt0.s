.global _start
_start:
    # Initialize sp to end of memory (set by emulator_runner)
    # Call main
    jal ra, main
    
    # Call exit with return value from main (in a0)
    li a7, 93        # exit syscall number
    ecall
    
    # Halt (in case exit fails)
    j .

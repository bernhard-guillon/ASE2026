/* Neural character generation program
 * 
 * This program demonstrates character-to-image generation using a trained
 * neural network model. It reads a character code from register a0 (x10),
 * runs the neural network forward pass, and writes the 400 bytes to
 * framebuffer memory at 0x20000 (matching static_char_gen.c interface).
 *
 * The neural network is compiled from the trained model and embedded
 * in the binary.
 */

/* Framebuffer address in memory (same as static_char_gen.c) */
#define FRAMEBUFFER_ADDR 0x20000

/* Forward declarations of neural network functions */
extern void run_neural_inference(int char_code);

int main() {
    register int char_code __asm__("a0");
    
    /* Run infinitely, reading a0 each iteration and updating framebuffer */
    while (1) {
        /* Read current character code from a0 register */
        asm volatile ("" : "=r" (char_code) : "0" (char_code));
        
        /* Validate character code is in valid ASCII range [0, 254] */
        if (char_code < 255) {
            /* Call neural network inference */
            run_neural_inference(char_code);
        }
        /* Loop continues; emulator will provide new a0 value each iteration */
    }
    
    return 0;  /* Unreachable, but needed for compilation */
}


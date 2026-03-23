/* Static character generation program
 * 
 * This program demonstrates character-to-image generation using a static font.
 * It reads a character code from register a0 (x10), looks up the pixel data
 * from the static font array, and writes the 400 bytes to memory.
 */

#include "character_font.h"

/* Framebuffer address in memory */
#define FRAMEBUFFER_ADDR 0x20000

int main() {
    unsigned char *framebuffer = (unsigned char *)FRAMEBUFFER_ADDR;
    
    /* Run infinitely, reading a0 each iteration and updating framebuffer */
    while (1) {
        /* Read current character code from a0 register */
        register int char_code __asm__("a0");
        
        /* Validate character code is in valid ASCII range [0, 254] */
        if (char_code < 255) {
            /* Get pointer to the 400 bytes of pixel data for this character */
            const unsigned char *pixels = char_images[char_code];
            
            /* Copy 400 bytes to framebuffer memory location */
            for (int i = 0; i < 400; ++i) {
                framebuffer[i] = pixels[i];
            }
        }
        /* Loop continues; Ctrl+C will terminate the emulator */
    }
    
    return 0;  /* Unreachable, but needed for compilation */
}



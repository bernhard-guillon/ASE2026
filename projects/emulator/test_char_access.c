#include "character_font.h"

#define FRAMEBUFFER_ADDR 0x20000

int main() {
    unsigned char *framebuffer = (unsigned char *)FRAMEBUFFER_ADDR;
    
    // Test character 65 (letter 'A')
    int char_code = 65;
    const unsigned char *pixels = char_images[char_code];
    
    // Copy first 10 bytes to framebuffer
    for (int i = 0; i < 10; ++i) {
        framebuffer[i] = pixels[i];
    }
    
    // Signal success - write a value to framebuffer
    framebuffer[10] = 123;
    
    return 0;
}

// Simple malloc/free implementation using mmap syscall
// This is a very basic allocator for testing purposes

#include <stddef.h>

void* mmap(void *addr, unsigned long len, int prot, int flags, int fd, long pgoffset);
int munmap(void *addr, unsigned long len);

// Simple memory allocator using mmap
// Returns NULL on error, allocated pointer on success
void* malloc(unsigned long size) {
    if (size == 0) {
        return 0;
    }
    
    // MAP_ANONYMOUS = 0x20
    // We let the kernel choose the address
    void* ptr = mmap(0, size, 0, 0x20, -1, 0);
    
    // mmap returns (void*)-1 on error, check for this
    if ((unsigned long)ptr == (unsigned long)-1) {
        return 0;
    }
    
    return ptr;
}

// Free memory allocated with malloc
// Returns 0 on success, -1 on error
int free(void *ptr) {
    if (ptr == 0) {
        return 0;  // free(NULL) is safe
    }
    
    // We don't track the original size, so we pass a dummy value
    // Real implementations would track metadata
    // For now, this is just a stub that returns success
    return 0;
}

// Free memory allocated with malloc (variadic version)
// This variant tries to work even if we don't know the size
void free_safe(void *ptr, unsigned long size) {
    if (ptr == 0) {
        return;
    }
    
    munmap(ptr, size);
}

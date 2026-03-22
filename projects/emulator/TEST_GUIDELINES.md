# Test Guidelines for the RISC-V Emulator

This document captures common pitfalls found during test development, along with
rules to follow when writing new tests.  Load this file into the implementing
agent before asking it to write tests.

---

## 1. Bare-metal C blackbox tests – no libc allowed

**Context:** Every C file under `blackbox_tests/c/` is compiled with
`-nostdlib`.  The linker only sees `crt0.s`, `syscalls.s`, and the test source
file itself.

### ❌ DO NOT
```c
#include <stdio.h>          // libc is not present
#include <stdlib.h>
#include <string.h>
printf("value = %f\n", x); // requires libc + libgcc (__extendsfdf2 etc.)
sprintf / fprintf / scanf   // same reason
```

### ✅ DO
```c
/* Declare only the syscalls implemented by syscalls.s */
extern int write(int fd, const void *buf, unsigned long count);

static void write_str(const char *s) {
    unsigned long len = 0;
    while (s[len]) len++;
    write(1, s, len);
}

write_str("PASS: my test\n");
```

### Why `%f` breaks the build

Even though the project uses `-march=rv32imf` (hardware single-precision FP),
`printf("%f", x)` converts the `float` to `double` internally, which calls
`__extendsfdf2` from *libgcc*.  Without `-lgcc` in the link command, this
symbol is unresolved and the build fails.

**Rule:** In bare-metal tests, never mix `float`/`double` with format strings.
Use direct comparisons (`if (x == 6.0f)`) and write fixed "PASS"/"FAIL" strings
via `write()`.

---

## 2. Emulator memory size in unit tests

**Context:** `Emulator` has a 1 GB default memory size (required for `mmap`
support at runtime).  Constructing a 1 GB emulator per GTest fixture causes each
test to take ~1.5 s (allocation + zero-fill).

### ❌ DO NOT
```cpp
class MyTest : public ::testing::Test {
protected:
    Emulator emulator;           // 1 GB – very slow per test
    void SetUp() override { emulator.reset(); }
};
```

### ✅ DO
```cpp
class MyTest : public ::testing::Test {
protected:
    Emulator emulator{64 * 1024};  // 64 KB is enough for unit tests
    void SetUp() override { emulator.reset(); }
};
```

Use the smallest size that covers the addresses your test touches:
| Use-case                | Recommended size |
|-------------------------|-----------------|
| Single instruction test | 64 KB (`64*1024`) |
| Multi-instruction / small programs | 256 KB (`256*1024`) |
| mmap / syscall tests | 256 KB–1 MB as needed |
| Full model execution | Keep the large default |

---

## 3. Floating-point in bare-metal code

When writing C blackbox tests that exercise FP instructions:

* Only use `float` (single precision).  Avoid `double` implicitly or explicitly.
* Comparisons on exact representable values (powers of two, simple fractions) are
  fine: `if (result == 6.0f)`.
* For values that are not exactly representable, compare with a tolerance:
  ```c
  /* integer bit-pattern comparison – no libm needed */
  unsigned int bits;
  __builtin_memcpy(&bits, &result, 4);
  if (bits == 0x40C90FDB) { /* check exact π bits */ }
  ```
* Do **not** use `fabsf`, `sqrtf`, or any `<math.h>` function – those require
  libm which is not linked.

---

## 4. Output format for blackbox C tests

* Use only `write(1, ...)` for stdout output.
* Terminate every line with `\n`.
* Keep each message on a single line; do not embed newlines inside a string.
* Return `0` from `main` if all tests pass, non-zero otherwise.
* Do **not** add an `expected.txt` for C tests unless you also update
  `BlackboxTests.cmake` to validate stdout – currently C tests are validated by
  exit code only.

---

## 5. Output format for blackbox assembly tests

* Provide both `config.txt` and `expected.txt` in the test directory.
* `config.txt` supports the following keys (one per line):
  ```
  march=rv32imf        # default: rv32i
  exit_code=0          # default: 0
  timeout_ms=1000      # default: 1000
  ```
* `expected.txt` currently stores the expected exit code (`exit_code: 0`).
  The test runner (CTest) only checks that the emulator exits without error.

---

## 6. Quick checklist before opening a PR

- [ ] Does every C blackbox test compile with `-nostdlib`?  (No `#include <stdio.h>` etc.)
- [ ] Does every new GTest fixture specify an appropriate `Emulator` memory size?
- [ ] Are all `float` operations free of implicit `double` conversions?
- [ ] Do all blackbox ASM tests have both `config.txt` and `expected.txt`?
- [ ] Does `ctest --output-on-failure` pass locally?

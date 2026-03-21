FROM archlinux:latest

# Update system packages
RUN pacman -Syu --noconfirm

# Install build dependencies, RISC-V toolchain, and Python test dependencies
RUN pacman -S --noconfirm \
    base-devel \
    cmake \
    gcc \
    git \
    python \
    python-pytest \
    python-numpy \
    riscv64-elf-binutils \
    riscv64-elf-gcc \
    riscv64-elf-newlib \
    riscv64-elf-gdb

WORKDIR /workspace

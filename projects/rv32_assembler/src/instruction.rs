//! Instruction definitions for RV32I and RV32F

use std::fmt;

/// RISC-V 32-bit register names
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Register {
    X0,  X1,  X2,  X3,  X4,  X5,  X6,  X7,
    X8,  X9,  X10, X11, X12, X13, X14, X15,
    X16, X17, X18, X19, X20, X21, X22, X23,
    X24, X25, X26, X27, X28, X29, X30, X31,
}

impl Register {
    pub fn number(self) -> u32 {
        match self {
            Register::X0 => 0, Register::X1 => 1, Register::X2 => 2, Register::X3 => 3,
            Register::X4 => 4, Register::X5 => 5, Register::X6 => 6, Register::X7 => 7,
            Register::X8 => 8, Register::X9 => 9, Register::X10 => 10, Register::X11 => 11,
            Register::X12 => 12, Register::X13 => 13, Register::X14 => 14, Register::X15 => 15,
            Register::X16 => 16, Register::X17 => 17, Register::X18 => 18, Register::X19 => 19,
            Register::X20 => 20, Register::X21 => 21, Register::X22 => 22, Register::X23 => 23,
            Register::X24 => 24, Register::X25 => 25, Register::X26 => 26, Register::X27 => 27,
            Register::X28 => 28, Register::X29 => 29, Register::X30 => 30, Register::X31 => 31,
        }
    }

    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "x0" | "zero" => Some(Register::X0),
            "x1" | "ra" => Some(Register::X1),
            "x2" | "sp" => Some(Register::X2),
            "x3" | "gp" => Some(Register::X3),
            "x4" | "tp" => Some(Register::X4),
            "x5" | "t0" => Some(Register::X5),
            "x6" | "t1" => Some(Register::X6),
            "x7" | "t2" => Some(Register::X7),
            "x8" | "s0" | "fp" => Some(Register::X8),
            "x9" | "s1" => Some(Register::X9),
            "x10" | "a0" => Some(Register::X10),
            "x11" | "a1" => Some(Register::X11),
            "x12" | "a2" => Some(Register::X12),
            "x13" | "a3" => Some(Register::X13),
            "x14" | "a4" => Some(Register::X14),
            "x15" | "a5" => Some(Register::X15),
            "x16" | "a6" => Some(Register::X16),
            "x17" | "a7" => Some(Register::X17),
            "x18" | "s2" => Some(Register::X18),
            "x19" | "s3" => Some(Register::X19),
            "x20" | "s4" => Some(Register::X20),
            "x21" | "s5" => Some(Register::X21),
            "x22" | "s6" => Some(Register::X22),
            "x23" | "s7" => Some(Register::X23),
            "x24" | "s8" => Some(Register::X24),
            "x25" | "s9" => Some(Register::X25),
            "x26" | "s10" => Some(Register::X26),
            "x27" | "s11" => Some(Register::X27),
            "x28" | "t3" => Some(Register::X28),
            "x29" | "t4" => Some(Register::X29),
            "x30" | "t5" => Some(Register::X30),
            "x31" | "t6" => Some(Register::X31),
            _ => None,
        }
    }
}

impl fmt::Display for Register {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "x{}", self.number())
    }
}

/// Floating-point registers (RV32F)
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FloatRegister {
    F0,  F1,  F2,  F3,  F4,  F5,  F6,  F7,
    F8,  F9,  F10, F11, F12, F13, F14, F15,
    F16, F17, F18, F19, F20, F21, F22, F23,
    F24, F25, F26, F27, F28, F29, F30, F31,
}

impl FloatRegister {
    pub fn number(self) -> u32 {
        match self {
            FloatRegister::F0 => 0, FloatRegister::F1 => 1, FloatRegister::F2 => 2, FloatRegister::F3 => 3,
            FloatRegister::F4 => 4, FloatRegister::F5 => 5, FloatRegister::F6 => 6, FloatRegister::F7 => 7,
            FloatRegister::F8 => 8, FloatRegister::F9 => 9, FloatRegister::F10 => 10, FloatRegister::F11 => 11,
            FloatRegister::F12 => 12, FloatRegister::F13 => 13, FloatRegister::F14 => 14, FloatRegister::F15 => 15,
            FloatRegister::F16 => 16, FloatRegister::F17 => 17, FloatRegister::F18 => 18, FloatRegister::F19 => 19,
            FloatRegister::F20 => 20, FloatRegister::F21 => 21, FloatRegister::F22 => 22, FloatRegister::F23 => 23,
            FloatRegister::F24 => 24, FloatRegister::F25 => 25, FloatRegister::F26 => 26, FloatRegister::F27 => 27,
            FloatRegister::F28 => 28, FloatRegister::F29 => 29, FloatRegister::F30 => 30, FloatRegister::F31 => 31,
        }
    }

    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "f0" | "ft0" => Some(FloatRegister::F0),
            "f1" | "ft1" => Some(FloatRegister::F1),
            "f2" | "ft2" => Some(FloatRegister::F2),
            "f3" | "ft3" => Some(FloatRegister::F3),
            "f4" | "ft4" => Some(FloatRegister::F4),
            "f5" | "ft5" => Some(FloatRegister::F5),
            "f6" | "ft6" => Some(FloatRegister::F6),
            "f7" | "ft7" => Some(FloatRegister::F7),
            "f8" | "fs0" => Some(FloatRegister::F8),
            "f9" | "fs1" => Some(FloatRegister::F9),
            "f10" | "fa0" => Some(FloatRegister::F10),
            "f11" | "fa1" => Some(FloatRegister::F11),
            "f12" | "fa2" => Some(FloatRegister::F12),
            "f13" | "fa3" => Some(FloatRegister::F13),
            "f14" | "fa4" => Some(FloatRegister::F14),
            "f15" | "fa5" => Some(FloatRegister::F15),
            "f16" | "fa6" => Some(FloatRegister::F16),
            "f17" | "fa7" => Some(FloatRegister::F17),
            "f18" | "fs2" => Some(FloatRegister::F18),
            "f19" | "fs3" => Some(FloatRegister::F19),
            "f20" | "fs4" => Some(FloatRegister::F20),
            "f21" | "fs5" => Some(FloatRegister::F21),
            "f22" | "fs6" => Some(FloatRegister::F22),
            "f23" | "fs7" => Some(FloatRegister::F23),
            "f24" | "fs8" => Some(FloatRegister::F24),
            "f25" | "fs9" => Some(FloatRegister::F25),
            "f26" | "fs10" => Some(FloatRegister::F26),
            "f27" | "fs11" => Some(FloatRegister::F27),
            "f28" | "ft8" => Some(FloatRegister::F28),
            "f29" | "ft9" => Some(FloatRegister::F29),
            "f30" | "ft10" => Some(FloatRegister::F30),
            "f31" | "ft11" => Some(FloatRegister::F31),
            _ => None,
        }
    }
}

impl fmt::Display for FloatRegister {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "f{}", self.number())
    }
}

/// Parsed instruction (intermediate representation)
#[derive(Debug, Clone, PartialEq)]
pub enum Instruction {
    // RV32I - R-type (add, sub, and, or, xor, sll, srl, sra)
    RType {
        mnemonic: String,
        rd: Register,
        rs1: Register,
        rs2: Register,
    },
    // RV32I - I-type (addi, andi, ori, xori, slli, srli, srai, lw, lh, lb, lwu, lhu)
    IType {
        mnemonic: String,
        rd: Register,
        rs1: Register,
        imm: i64,
    },
    // RV32I - S-type (sw, sh, sb)
    SType {
        mnemonic: String,
        rs1: Register,
        rs2: Register,
        imm: i64,
    },
    // RV32I - B-type (beq, bne, blt, bltu, bge, bgeu)
    BType {
        mnemonic: String,
        rs1: Register,
        rs2: Register,
        imm: i64,
    },
    // RV32I - U-type (lui, auipc)
    UType {
        mnemonic: String,
        rd: Register,
        imm: i64,
    },
    // RV32I - J-type (jal)
    JType {
        mnemonic: String,
        rd: Register,
        imm: i64,
    },
    // RV32F - FR-type (fadd.s, fsub.s, fmul.s, fdiv.s)
    FRType {
        mnemonic: String,
        rd: FloatRegister,
        rs1: FloatRegister,
        rs2: FloatRegister,
    },
    // RV32F - FI-type (flw)
    FIType {
        mnemonic: String,
        rd: FloatRegister,
        rs1: Register,
        imm: i64,
    },
    // RV32F - FS-type (fsw)
    FSType {
        mnemonic: String,
        rs1: Register,
        rs2: FloatRegister,
        imm: i64,
    },
    // RV32F - FC-type (feq.s, flt.s, fle.s)
    FCType {
        mnemonic: String,
        rd: Register,
        rs1: FloatRegister,
        rs2: FloatRegister,
    },
    // RV32F - FCVT-type (fcvt.w.s, fcvt.s.w)
    FCvtType {
        mnemonic: String,
        rd: Register,
        rs1: FloatRegister,
    },
    // RV32F - FCVT reverse (fcvt.s.w reads int from rd, writes float to rs1)
    FCvtRevType {
        mnemonic: String,
        rd: FloatRegister,
        rs1: Register,
    },
    // RV32F - FMOVE (fmv.x.w, fmv.w.x)
    FMoveType {
        mnemonic: String,
        rd: Register,
        rs1: FloatRegister,
    },
    FMoveRevType {
        mnemonic: String,
        rd: FloatRegister,
        rs1: Register,
    },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_register_parsing() {
        assert_eq!(Register::from_name("x0"), Some(Register::X0));
        assert_eq!(Register::from_name("x31"), Some(Register::X31));
        assert_eq!(Register::from_name("sp"), Some(Register::X2));
        assert_eq!(Register::from_name("a0"), Some(Register::X10));
        assert_eq!(Register::from_name("invalid"), None);
    }

    #[test]
    fn test_float_register_parsing() {
        assert_eq!(FloatRegister::from_name("f0"), Some(FloatRegister::F0));
        assert_eq!(FloatRegister::from_name("f31"), Some(FloatRegister::F31));
        assert_eq!(FloatRegister::from_name("fa0"), Some(FloatRegister::F10));
        assert_eq!(FloatRegister::from_name("ft11"), Some(FloatRegister::F31));
        assert_eq!(FloatRegister::from_name("x0"), None);
    }

    #[test]
    fn test_register_numbers() {
        assert_eq!(Register::X0.number(), 0);
        assert_eq!(Register::X10.number(), 10);
        assert_eq!(Register::X31.number(), 31);
    }

    #[test]
    fn test_float_register_numbers() {
        assert_eq!(FloatRegister::F0.number(), 0);
        assert_eq!(FloatRegister::F15.number(), 15);
        assert_eq!(FloatRegister::F31.number(), 31);
    }
}

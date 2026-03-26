//! Encoder: convert instruction representation to 32-bit machine code

use crate::error::{AssemblerError, Result};
use crate::instruction::Instruction;

pub struct Encoder;

// RISC-V opcode constants
const OPCODE_LOAD: u32 = 0b0000011;    // LW, LH, LB, etc.
const OPCODE_I_ARITH: u32 = 0b0010011; // ADDI, ANDI, etc.
const OPCODE_R_ARITH: u32 = 0b0110011; // ADD, SUB, AND, OR, XOR, SLL, SRL, SRA
const OPCODE_STORE: u32 = 0b0100011;   // SW, SH, SB
const OPCODE_BRANCH: u32 = 0b1100011;  // BEQ, BNE, etc.
const OPCODE_LUI: u32 = 0b0110111;     // LUI
const OPCODE_AUIPC: u32 = 0b0010111;   // AUIPC
const OPCODE_JAL: u32 = 0b1101111;     // JAL
const OPCODE_JALR: u32 = 0b1100111;    // JALR
const OPCODE_SYSTEM: u32 = 0b1110011;  // ECALL, EBREAK
const OPCODE_FP_LOAD: u32 = 0b0000111; // FLW
const OPCODE_FP_STORE: u32 = 0b0100111; // FSW
const OPCODE_FP: u32 = 0b1010011;      // Floating-point operations

impl Encoder {
    pub fn encode(instruction: &Instruction) -> Result<[u8; 4]> {
        let word = match instruction {
            Instruction::RType {
                mnemonic,
                rd,
                rs1,
                rs2,
            } => Self::encode_r_type(mnemonic, rd.number(), rs1.number(), rs2.number())?,
            Instruction::IType { mnemonic, rd, rs1, imm } => {
                Self::encode_i_type(mnemonic, rd.number(), rs1.number(), *imm)?
            }
            Instruction::SType {
                mnemonic,
                rs1,
                rs2,
                imm,
            } => Self::encode_s_type(mnemonic, rs1.number(), rs2.number(), *imm)?,
            Instruction::BType {
                mnemonic,
                rs1,
                rs2,
                imm,
            } => Self::encode_b_type(mnemonic, rs1.number(), rs2.number(), *imm)?,
            Instruction::UType { mnemonic, rd, imm } => {
                Self::encode_u_type(mnemonic, rd.number(), *imm)?
            }
            Instruction::JType { mnemonic, rd, imm } => {
                Self::encode_j_type(mnemonic, rd.number(), *imm)?
            }
            Instruction::FRType {
                mnemonic,
                rd,
                rs1,
                rs2,
            } => Self::encode_f_r_type(mnemonic, rd.number(), rs1.number(), rs2.number())?,
            Instruction::FIType { mnemonic, rd, rs1, imm } => {
                Self::encode_f_i_type(mnemonic, rd.number(), rs1.number(), *imm)?
            }
            Instruction::FSType {
                mnemonic,
                rs1,
                rs2,
                imm,
            } => Self::encode_f_s_type(mnemonic, rs1.number(), rs2.number(), *imm)?,
            Instruction::FCType {
                mnemonic,
                rd,
                rs1,
                rs2,
            } => Self::encode_f_c_type(mnemonic, rd.number(), rs1.number(), rs2.number())?,
            Instruction::FCvtType { mnemonic, rd, rs1 } => {
                Self::encode_f_cvt_type(mnemonic, rd.number(), rs1.number())?
            }
            Instruction::FCvtRevType { mnemonic, rd, rs1 } => {
                Self::encode_f_cvt_rev_type(mnemonic, rd.number(), rs1.number())?
            }
            Instruction::FMoveType { mnemonic, rd, rs1 } => {
                Self::encode_f_move_type(mnemonic, rd.number(), rs1.number())?
            }
            Instruction::FMoveRevType { mnemonic, rd, rs1 } => {
                Self::encode_f_move_rev_type(mnemonic, rd.number(), rs1.number())?
            }
        };

        // Convert to little-endian bytes
        Ok(word.to_le_bytes())
    }

    fn encode_r_type(mnemonic: &str, rd: u32, rs1: u32, rs2: u32) -> Result<u32> {
        let (funct7, funct3) = match mnemonic {
            "add" => (0b0000000, 0b000),
            "sub" => (0b0100000, 0b000),
            "and" => (0b0000000, 0b111),
            "or" => (0b0000000, 0b110),
            "xor" => (0b0000000, 0b100),
            "sll" => (0b0000000, 0b001),
            "srl" => (0b0000000, 0b101),
            "sra" => (0b0100000, 0b101),
            "slt" => (0b0000000, 0b010),
            "sltu" => (0b0000000, 0b011),
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        // R-type encoding: [funct7:7 | rs2:5 | rs1:5 | funct3:3 | rd:5 | opcode:7]
        Ok(((funct7 & 0x7f) << 25) | ((rs2 & 0x1f) << 20) | ((rs1 & 0x1f) << 15)
            | ((funct3 & 0x7) << 12) | ((rd & 0x1f) << 7) | (OPCODE_R_ARITH & 0x7f))
    }

    fn encode_i_type(mnemonic: &str, rd: u32, rs1: u32, imm: i64) -> Result<u32> {
        // Special case: ecall and ebreak
        if mnemonic == "ecall" {
            // [0:12 | 0:5 | 0:5 | 0:3 | 0:5 | 0x73]
            return Ok(OPCODE_SYSTEM & 0x7f);
        }
        if mnemonic == "ebreak" {
            // [1:12 | 0:5 | 0:5 | 0:3 | 0:5 | 0x73]
            return Ok((1 << 20) | (OPCODE_SYSTEM & 0x7f));
        }

        let imm12 = Self::check_imm_range(imm, 12)?;

        let (funct3, opcode, funct7_for_shift) = match mnemonic {
            "addi" => (0b000, OPCODE_I_ARITH, None),
            "andi" => (0b111, OPCODE_I_ARITH, None),
            "ori" => (0b110, OPCODE_I_ARITH, None),
            "xori" => (0b100, OPCODE_I_ARITH, None),
            "slli" => (0b001, OPCODE_I_ARITH, Some(0b0000000)),
            "srli" => (0b101, OPCODE_I_ARITH, Some(0b0000000)),
            "srai" => (0b101, OPCODE_I_ARITH, Some(0b0100000)),
            "slti" => (0b010, OPCODE_I_ARITH, None),
            "sltiu" => (0b011, OPCODE_I_ARITH, None),
            "lw" => (0b010, OPCODE_LOAD, None),
            "lh" => (0b001, OPCODE_LOAD, None),
            "lb" => (0b000, OPCODE_LOAD, None),
            "lwu" => (0b110, OPCODE_LOAD, None),
            "lhu" => (0b101, OPCODE_LOAD, None),
            "lbu" => (0b100, OPCODE_LOAD, None),
            "jalr" => (0b000, OPCODE_JALR, None),
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        // For shifts, imm12 upper 7 bits are funct7
        let imm_bits = if let Some(f7) = funct7_for_shift {
            (f7 << 5) | (imm12 & 0x1f)  // funct7 in bits [11:5], shift amount in bits [4:0]
        } else {
            imm12
        };

        // I-type encoding: [imm12:20 | rs1:5 | funct3:3 | rd:5 | opcode:7]
        Ok((imm_bits << 20) | ((rs1 & 0x1f) << 15) | ((funct3 & 0x7) << 12) | ((rd & 0x1f) << 7) | (opcode & 0x7f))
    }

    fn encode_s_type(mnemonic: &str, rs1: u32, rs2: u32, imm: i64) -> Result<u32> {
        let imm12 = Self::check_imm_range(imm, 12)?;

        let (funct3, opcode) = match mnemonic {
            "sw" => (0b010, OPCODE_STORE),
            "sh" => (0b001, OPCODE_STORE),
            "sb" => (0b000, OPCODE_STORE),
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        // S-type: split immediate into upper 7 bits and lower 5 bits
        let imm_upper = (imm12 >> 5) & 0x7f;
        let imm_lower = imm12 & 0x1f;

        Ok(Self::encode_instruction(
            opcode, imm_lower, funct3, rs1, rs2, imm_upper, 0,
        ))
    }

    fn encode_b_type(mnemonic: &str, rs1: u32, rs2: u32, imm: i64) -> Result<u32> {
        let imm_val = Self::check_imm_range(imm, 13)?;

        let funct3 = match mnemonic {
            "beq" => 0b000,
            "bne" => 0b001,
            "blt" => 0b100,
            "bltu" => 0b110,
            "bge" => 0b101,
            "bgeu" => 0b111,
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        // B-type immediate encoding: [12|10:5][4:1|11]
        let imm_11 = (imm_val >> 11) & 1;
        let imm_4_1 = (imm_val >> 1) & 0xf;
        let imm_10_5 = (imm_val >> 5) & 0x3f;
        let imm_12 = (imm_val >> 12) & 1;

        let rd = (imm_4_1 << 8) | (imm_11 << 7);
        let funct7 = (imm_12 << 6) | imm_10_5;

        Ok(Self::encode_instruction(
            OPCODE_BRANCH, rd, funct3, rs1, rs2, funct7, 0,
        ))
    }

    fn encode_u_type(mnemonic: &str, rd: u32, imm: i64) -> Result<u32> {
        let imm20 = Self::check_imm_range(imm, 20)?;
        let opcode = match mnemonic {
            "lui" => OPCODE_LUI,
            "auipc" => OPCODE_AUIPC,
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        Ok(Self::encode_instruction(opcode, rd, 0, imm20 as u32, 0, 0, 0))
    }

    fn encode_j_type(mnemonic: &str, rd: u32, imm: i64) -> Result<u32> {
        if mnemonic != "jal" {
            return Err(AssemblerError::UnknownInstruction(mnemonic.to_string()));
        }

        let imm_val = Self::check_imm_range(imm, 21)?;

        // J-type immediate encoding: [20|10:1|11|19:12]
        let imm_20 = (imm_val >> 20) & 1;
        let imm_10_1 = (imm_val >> 1) & 0x3ff;
        let imm_11 = (imm_val >> 11) & 1;
        let imm_19_12 = (imm_val >> 12) & 0xff;

        let imm_enc = (imm_20 << 20) | (imm_19_12 << 12) | (imm_11 << 11) | (imm_10_1 << 1);

        Ok(Self::encode_instruction(
            OPCODE_JAL, rd, 0, imm_enc as u32, 0, 0, 0,
        ))
    }

    fn encode_f_r_type(mnemonic: &str, rd: u32, rs1: u32, rs2: u32) -> Result<u32> {
        let (funct7, _funct3) = match mnemonic {
            "fadd.s" => (0b0000000, 0b000),
            "fsub.s" => (0b0000100, 0b000),
            "fmul.s" => (0b0001000, 0b000),
            "fdiv.s" => (0b0001100, 0b000),
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        Ok(Self::encode_instruction(
            OPCODE_FP, rd, 0b000, rs1, rs2, funct7, 0,
        ))
    }

    fn encode_f_i_type(mnemonic: &str, rd: u32, rs1: u32, imm: i64) -> Result<u32> {
        if mnemonic != "flw" {
            return Err(AssemblerError::UnknownInstruction(mnemonic.to_string()));
        }

        let imm12 = Self::check_imm_range(imm, 12)?;
        Ok(Self::encode_instruction(
            OPCODE_FP_LOAD, rd, 0b010, rs1, imm12, 0, 0,
        ))
    }

    fn encode_f_s_type(mnemonic: &str, rs1: u32, rs2: u32, imm: i64) -> Result<u32> {
        if mnemonic != "fsw" {
            return Err(AssemblerError::UnknownInstruction(mnemonic.to_string()));
        }

        let imm12 = Self::check_imm_range(imm, 12)?;
        let imm_upper = (imm12 >> 5) & 0x7f;
        let imm_lower = imm12 & 0x1f;

        Ok(Self::encode_instruction(
            OPCODE_FP_STORE, imm_lower, 0b010, rs1, rs2, imm_upper, 0,
        ))
    }

    fn encode_f_c_type(mnemonic: &str, rd: u32, rs1: u32, rs2: u32) -> Result<u32> {
        let (funct7, _funct3) = match mnemonic {
            "feq.s" => (0b1010000, 0b010),
            "flt.s" => (0b1010000, 0b001),
            "fle.s" => (0b1010000, 0b000),
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        Ok(Self::encode_instruction(
            OPCODE_FP, rd, 0b000, rs1, rs2, funct7, 0,
        ))
    }

    fn encode_f_cvt_type(mnemonic: &str, rd: u32, rs1: u32) -> Result<u32> {
        if mnemonic != "fcvt.w.s" {
            return Err(AssemblerError::UnknownInstruction(mnemonic.to_string()));
        }

        // fcvt.w.s: funct7=1100000, rs2=00000
        Ok(Self::encode_instruction(
            OPCODE_FP, rd, 0b000, rs1, 0b00000, 0b1100000, 0,
        ))
    }

    fn encode_f_cvt_rev_type(mnemonic: &str, rd: u32, rs1: u32) -> Result<u32> {
        if mnemonic != "fcvt.s.w" {
            return Err(AssemblerError::UnknownInstruction(mnemonic.to_string()));
        }

        // fcvt.s.w: funct7=1101000, rs2=00000
        Ok(Self::encode_instruction(
            OPCODE_FP, rd, 0b000, rs1, 0b00000, 0b1101000, 0,
        ))
    }

    fn encode_f_move_type(mnemonic: &str, rd: u32, rs1: u32) -> Result<u32> {
        if mnemonic != "fmv.x.w" {
            return Err(AssemblerError::UnknownInstruction(mnemonic.to_string()));
        }

        // fmv.x.w: funct7=1110000, rs2=00000
        Ok(Self::encode_instruction(
            OPCODE_FP, rd, 0b000, rs1, 0b00000, 0b1110000, 0,
        ))
    }

    fn encode_f_move_rev_type(mnemonic: &str, rd: u32, rs1: u32) -> Result<u32> {
        if mnemonic != "fmv.w.x" {
            return Err(AssemblerError::UnknownInstruction(mnemonic.to_string()));
        }

        // fmv.w.x: funct7=1111000, rs2=00000
        Ok(Self::encode_instruction(
            OPCODE_FP, rd, 0b000, rs1, 0b00000, 0b1111000, 0,
        ))
    }

    // Encode 32-bit instruction word with fields
    // Layout: [funct7:7][rs2:5][rs1:5][funct3:3][rd:5][opcode:7]
    fn encode_instruction(
        opcode: u32,
        rd: u32,
        funct3: u32,
        rs1: u32,
        rs2: u32,
        funct7: u32,
        _unused: u32,
    ) -> u32 {
        ((funct7 & 0x7f) << 25)
            | ((rs2 & 0x1f) << 20)
            | ((rs1 & 0x1f) << 15)
            | ((funct3 & 0x7) << 12)
            | ((rd & 0x1f) << 7)
            | (opcode & 0x7f)
    }

    fn check_imm_range(imm: i64, bits: usize) -> Result<u32> {
        let max_positive = (1i64 << (bits - 1)) - 1;
        let min_negative = -(1i64 << (bits - 1));

        if imm > max_positive || imm < min_negative {
            return Err(AssemblerError::InvalidImmediate(
                imm,
                format!("i{}", bits),
            ));
        }

        // Convert to unsigned representation for masking
        let mask = (1u64 << bits) - 1;
        Ok((imm as u64 & mask) as u32)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::instruction::{Instruction, Register};

    #[test]
    fn test_encode_addi() {
        let instr = Instruction::IType {
            mnemonic: "addi".to_string(),
            rd: Register::X1,
            rs1: Register::X0,
            imm: 42,
        };

        let result = Encoder::encode(&instr);
        assert!(result.is_ok());

        let bytes = result.unwrap();
        assert_eq!(bytes.len(), 4);

        // Verify it's valid instruction (opcode should be 0b0010011)
        let word = u32::from_le_bytes(bytes);
        let opcode = word & 0x7f;
        assert_eq!(opcode, 0b0010011); // I-type arithmetic opcode
    }

    #[test]
    fn test_encode_add() {
        let instr = Instruction::RType {
            mnemonic: "add".to_string(),
            rd: Register::X1,
            rs1: Register::X2,
            rs2: Register::X3,
        };

        let result = Encoder::encode(&instr);
        assert!(result.is_ok());

        let bytes = result.unwrap();
        let word = u32::from_le_bytes(bytes);
        let opcode = word & 0x7f;
        let rd = (word >> 7) & 0x1f;
        assert_eq!(opcode, 0b0010011);
        assert_eq!(rd, 1); // x1
    }

    #[test]
    fn test_immediate_range_check() {
        // 12-bit imm range: [-2048, 2047]
        assert!(Encoder::check_imm_range(2047, 12).is_ok());
        assert!(Encoder::check_imm_range(-2048, 12).is_ok());
        assert!(Encoder::check_imm_range(2048, 12).is_err());
        assert!(Encoder::check_imm_range(-2049, 12).is_err());
    }
}

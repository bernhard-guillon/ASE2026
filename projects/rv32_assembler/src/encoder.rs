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
const OPCODE_CUSTOM0: u32 = 0b1110111; // Neural custom extension v1 (0x77)
const OPCODE_CUSTOM3: u32 = 0b1111011; // Neural custom extension v2 preview (0x7B)

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
            Instruction::NType {
                mnemonic,
                rd,
                rs1,
                rs2,
                rs3,
            } => Self::encode_n_type(
                mnemonic,
                rd.number(),
                rs1.number(),
                rs2.number(),
                rs3.number(),
            )?,
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
        Ok(((imm_bits & 0xFFF) << 20)
            | ((rs1 & 0x1f) << 15)
            | ((funct3 & 0x7) << 12)
            | ((rd & 0x1f) << 7)
            | (opcode & 0x7f))
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

        Ok(((imm_12 & 0x1) << 31)
            | ((imm_10_5 & 0x3f) << 25)
            | ((rs2 & 0x1f) << 20)
            | ((rs1 & 0x1f) << 15)
            | ((funct3 & 0x7) << 12)
            | ((imm_4_1 & 0xf) << 8)
            | ((imm_11 & 0x1) << 7)
            | OPCODE_BRANCH)
    }

    fn encode_u_type(mnemonic: &str, rd: u32, imm: i64) -> Result<u32> {
        // U-type immediate is a raw 20-bit field (not sign-checked as I/B/J immediates).
        let imm20 = if (0..=0xFFFFF).contains(&imm) {
            imm as u32
        } else {
            return Err(AssemblerError::InvalidImmediate(
                imm,
                "u20".to_string(),
            ));
        };
        let opcode = match mnemonic {
            "lui" => OPCODE_LUI,
            "auipc" => OPCODE_AUIPC,
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        Ok(((imm20 & 0xFFFFF) << 12) | ((rd & 0x1f) << 7) | (opcode & 0x7f))
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

        Ok(((imm_20 & 0x1) << 31)
            | ((imm_19_12 & 0xff) << 12)
            | ((imm_11 & 0x1) << 20)
            | ((imm_10_1 & 0x3ff) << 21)
            | ((rd & 0x1f) << 7)
            | OPCODE_JAL)
    }

    fn encode_f_r_type(mnemonic: &str, rd: u32, rs1: u32, rs2: u32) -> Result<u32> {
        let (funct7, funct3) = match mnemonic {
            // For arithmetic FP ops without explicit rm suffix, GNU emits rm=111 (dynamic).
            "fadd.s" => (0b0000000, 0b111),
            "fsub.s" => (0b0000100, 0b111),
            "fmul.s" => (0b0001000, 0b111),
            "fdiv.s" => (0b0001100, 0b111),
            "fmin.s" => (0b0010100, 0b000),
            "fmax.s" => (0b0010100, 0b001),
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        Ok(Self::encode_instruction(
            OPCODE_FP, rd, funct3, rs1, rs2, funct7, 0,
        ))
    }

    fn encode_f_i_type(mnemonic: &str, rd: u32, rs1: u32, imm: i64) -> Result<u32> {
        if mnemonic != "flw" {
            return Err(AssemblerError::UnknownInstruction(mnemonic.to_string()));
        }

        let imm12 = Self::check_imm_range(imm, 12)?;
        Ok(((imm12 & 0xFFF) << 20)
            | ((rs1 & 0x1f) << 15)
            | (0b010 << 12)
            | ((rd & 0x1f) << 7)
            | OPCODE_FP_LOAD)
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
        let (funct7, funct3) = match mnemonic {
            "feq.s" => (0b1010000, 0b010),
            "flt.s" => (0b1010000, 0b001),
            "fle.s" => (0b1010000, 0b000),
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        Ok(Self::encode_instruction(
            OPCODE_FP, rd, funct3, rs1, rs2, funct7, 0,
        ))
    }

    fn encode_f_cvt_type(mnemonic: &str, rd: u32, rs1: u32) -> Result<u32> {
        let rs2 = match mnemonic {
            // fcvt.w.s: funct7=1100000, rs2=00000 (signed int result)
            "fcvt.w.s" => 0b00000,
            // fcvt.wu.s: funct7=1100000, rs2=00001 (unsigned int result)
            "fcvt.wu.s" => 0b00001,
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        Ok(Self::encode_instruction(
            OPCODE_FP, rd, 0b111, rs1, rs2, 0b1100000, 0,
        ))
    }

    fn encode_f_cvt_rev_type(mnemonic: &str, rd: u32, rs1: u32) -> Result<u32> {
        if mnemonic != "fcvt.s.w" {
            return Err(AssemblerError::UnknownInstruction(mnemonic.to_string()));
        }

        // fcvt.s.w: funct7=1101000, rs2=00000
        Ok(Self::encode_instruction(
            OPCODE_FP, rd, 0b111, rs1, 0b00000, 0b1101000, 0,
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

    fn encode_n_type(mnemonic: &str, rd: u32, rs1: u32, rs2: u32, rs3: u32) -> Result<u32> {
        // Custom compact neural format:
        // [31:27]=opid [26:22]=rs3 [21:17]=rs2 [16:12]=rs1 [11:7]=rd [6:0]=opcode(0x77/0x7B)
        //
        // nmatvec*.f32 uses only rd/rs1. rs2/rs3 must be zero for canonical encoding.
        let (opid, opcode, canonical_desc) = match mnemonic {
            "nmatvec.f32" => (0u32, OPCODE_CUSTOM0, true),
            "nvrelu.f32" => (1u32, OPCODE_CUSTOM0, false),
            "nvsigpwl.f32" => (2u32, OPCODE_CUSTOM0, false),
            "nvclampu8.f32" => (3u32, OPCODE_CUSTOM0, false),
            "nmatvecx.f32" => (0u32, OPCODE_CUSTOM3, true),
            "nmatvec4x.f32" => (4u32, OPCODE_CUSTOM3, true),
            "nmatvec8x.f32" => (5u32, OPCODE_CUSTOM3, true),
            "nmatvec8xp.f32" => (6u32, OPCODE_CUSTOM3, true),
            "nvrelux.f32" => (1u32, OPCODE_CUSTOM3, false),
            "nvsigpwlx.f32" => (2u32, OPCODE_CUSTOM3, false),
            "nvclampu8x.f32" => (3u32, OPCODE_CUSTOM3, false),
            _ => return Err(AssemblerError::UnknownInstruction(mnemonic.to_string())),
        };

        let (packed_rs2, packed_rs3) = if canonical_desc {
            (0u32, 0u32)
        } else {
            (rs2, rs3)
        };

        Ok(((opid & 0x1f) << 27)
            | ((packed_rs3 & 0x1f) << 22)
            | ((packed_rs2 & 0x1f) << 17)
            | ((rs1 & 0x1f) << 12)
            | ((rd & 0x1f) << 7)
            | opcode)
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
    use crate::instruction::{FloatRegister, Instruction, Register};

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
        assert_eq!(opcode, 0b0110011);
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

    #[test]
    fn test_encode_fcvt_wu_s() {
        let instr = Instruction::FCvtType {
            mnemonic: "fcvt.wu.s".to_string(),
            rd: Register::X30,   // t5
            rs1: FloatRegister::F10, // fa0
        };

        let bytes = Encoder::encode(&instr).unwrap();
        let word = u32::from_le_bytes(bytes);
        assert_eq!(word & 0x7f, 0b1010011);
        assert_eq!((word >> 20) & 0x1f, 1); // rs2=1 for unsigned conversion
    }

    #[test]
    fn test_encode_nmatvec_opcode_and_funct7() {
        let instr = Instruction::NType {
            mnemonic: "nmatvec.f32".to_string(),
            rd: Register::X6,
            rs1: Register::X5,
            rs2: Register::X0,
            rs3: Register::X0,
        };
        let bytes = Encoder::encode(&instr).unwrap();
        let word = u32::from_le_bytes(bytes);
        assert_eq!(word & 0x7f, 0x77);
        assert_eq!((word >> 27) & 0x1f, 0);
        assert_eq!((word >> 12) & 0x1f, 5);
        assert_eq!((word >> 17) & 0x1f, 0);
        assert_eq!((word >> 22) & 0x1f, 0);
    }

    #[test]
    fn test_encode_nvrelu_register_fields() {
        let instr = Instruction::NType {
            mnemonic: "nvrelu.f32".to_string(),
            rd: Register::X10,
            rs1: Register::X11,
            rs2: Register::X12,
            rs3: Register::X13,
        };
        let bytes = Encoder::encode(&instr).unwrap();
        let word = u32::from_le_bytes(bytes);
        assert_eq!(word & 0x7f, 0x77);
        assert_eq!((word >> 27) & 0x1f, 1);
        assert_eq!((word >> 12) & 0x1f, 11);
        assert_eq!((word >> 7) & 0x1f, 10);
        assert_eq!((word >> 17) & 0x1f, 12);
        assert_eq!((word >> 22) & 0x1f, 13);
    }

    #[test]
    fn test_encode_nvsigpwl_and_nvclamp_opids() {
        let sig = Instruction::NType {
            mnemonic: "nvsigpwl.f32".to_string(),
            rd: Register::X1,
            rs1: Register::X2,
            rs2: Register::X3,
            rs3: Register::X4,
        };
        let clamp = Instruction::NType {
            mnemonic: "nvclampu8.f32".to_string(),
            rd: Register::X1,
            rs1: Register::X2,
            rs2: Register::X3,
            rs3: Register::X4,
        };
        let sig_word = u32::from_le_bytes(Encoder::encode(&sig).unwrap());
        let clamp_word = u32::from_le_bytes(Encoder::encode(&clamp).unwrap());
        assert_eq!((sig_word >> 27) & 0x1f, 2);
        assert_eq!((clamp_word >> 27) & 0x1f, 3);
    }

    #[test]
    fn test_encode_nmatvecx_opcode_and_funct7() {
        let instr = Instruction::NType {
            mnemonic: "nmatvecx.f32".to_string(),
            rd: Register::X6,
            rs1: Register::X5,
            rs2: Register::X31,
            rs3: Register::X31,
        };
        let bytes = Encoder::encode(&instr).unwrap();
        let word = u32::from_le_bytes(bytes);
        assert_eq!(word & 0x7f, 0x7b);
        assert_eq!((word >> 27) & 0x1f, 0);
        assert_eq!((word >> 12) & 0x1f, 5);
        // Canonical nmatvec* form must zero rs2/rs3 fields regardless of inputs.
        assert_eq!((word >> 17) & 0x1f, 0);
        assert_eq!((word >> 22) & 0x1f, 0);
    }

    #[test]
    fn test_encode_nvrelux_opcode_and_register_fields() {
        let instr = Instruction::NType {
            mnemonic: "nvrelux.f32".to_string(),
            rd: Register::X10,
            rs1: Register::X11,
            rs2: Register::X12,
            rs3: Register::X13,
        };
        let bytes = Encoder::encode(&instr).unwrap();
        let word = u32::from_le_bytes(bytes);
        assert_eq!(word & 0x7f, 0x7b);
        assert_eq!((word >> 27) & 0x1f, 1);
        assert_eq!((word >> 12) & 0x1f, 11);
        assert_eq!((word >> 7) & 0x1f, 10);
        assert_eq!((word >> 17) & 0x1f, 12);
        assert_eq!((word >> 22) & 0x1f, 13);
    }

    #[test]
    fn test_encode_nmatvec4x_opcode_and_opid() {
        let instr = Instruction::NType {
            mnemonic: "nmatvec4x.f32".to_string(),
            rd: Register::X6,
            rs1: Register::X5,
            rs2: Register::X31,
            rs3: Register::X31,
        };
        let bytes = Encoder::encode(&instr).unwrap();
        let word = u32::from_le_bytes(bytes);
        assert_eq!(word & 0x7f, 0x7b);
        assert_eq!((word >> 27) & 0x1f, 4);
        assert_eq!((word >> 12) & 0x1f, 5);
        // Canonical descriptor form: rs2/rs3 must be zeroed.
        assert_eq!((word >> 17) & 0x1f, 0);
        assert_eq!((word >> 22) & 0x1f, 0);
    }

    #[test]
    fn test_encode_nmatvec8x_opcode_and_opid() {
        let instr = Instruction::NType {
            mnemonic: "nmatvec8x.f32".to_string(),
            rd: Register::X6,
            rs1: Register::X5,
            rs2: Register::X31,
            rs3: Register::X31,
        };
        let bytes = Encoder::encode(&instr).unwrap();
        let word = u32::from_le_bytes(bytes);
        assert_eq!(word & 0x7f, 0x7b);
        assert_eq!((word >> 27) & 0x1f, 5);
        assert_eq!((word >> 12) & 0x1f, 5);
        // Canonical descriptor form: rs2/rs3 must be zeroed.
        assert_eq!((word >> 17) & 0x1f, 0);
        assert_eq!((word >> 22) & 0x1f, 0);
    }

    #[test]
    fn test_encode_nmatvec8xp_opcode_and_opid() {
        let instr = Instruction::NType {
            mnemonic: "nmatvec8xp.f32".to_string(),
            rd: Register::X6,
            rs1: Register::X5,
            rs2: Register::X31,
            rs3: Register::X31,
        };
        let bytes = Encoder::encode(&instr).unwrap();
        let word = u32::from_le_bytes(bytes);
        assert_eq!(word & 0x7f, 0x7b);
        assert_eq!((word >> 27) & 0x1f, 6);
        assert_eq!((word >> 12) & 0x1f, 5);
        // Canonical descriptor form: rs2/rs3 must be zeroed.
        assert_eq!((word >> 17) & 0x1f, 0);
        assert_eq!((word >> 22) & 0x1f, 0);
    }
}

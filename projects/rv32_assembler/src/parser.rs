//! Parser: convert tokens to instruction representation

use crate::error::{AssemblerError, Result};
use crate::instruction::{FloatRegister, Instruction, Register};
use crate::lexer::Token;

pub struct Parser;

impl Parser {
    pub fn parse_instruction(tokens: &[Token]) -> Result<Option<Instruction>> {
        if tokens.is_empty() {
            return Ok(None);
        }

        // Skip directives, labels, and strings (return None to indicate no instruction)
        match &tokens[0] {
            Token::Directive(_) | Token::Label(_) | Token::String(_) => {
                return Ok(None);
            }
            _ => {}
        }

        let raw_mnemonic = match &tokens[0] {
            Token::Mnemonic(m) => m.to_lowercase(),
            _ => {
                return Err(AssemblerError::ParserError(
                    "expected mnemonic".to_string(),
                ))
            }
        };

        // Accept GNU aliases for move instructions.
        let mnemonic = match raw_mnemonic.as_str() {
            "fmv.s.x" => "fmv.w.x".to_string(),
            "fmv.x.s" => "fmv.x.w".to_string(),
            _ => raw_mnemonic,
        };

        // Handle pseudo-instructions
        match mnemonic.as_str() {
            "li" => return Ok(None), // Will be expanded at assemble_line level
            "la" => return Ok(None), // Skip label addresses without symbol table
            _ => {}
        }

        match mnemonic.as_str() {
            // Special instructions with no operands
            "ecall" | "ebreak" => {
                if tokens.len() != 1 {
                    return Err(AssemblerError::WrongOperandCount(
                        mnemonic.clone(),
                        0,
                        tokens.len() - 1,
                    ));
                }
                Ok(Some(Instruction::IType {
                    mnemonic,
                    rd: Register::X0,
                    rs1: Register::X0,
                    imm: 0,
                }))
            }
            // RV32I R-type instructions
            "add" | "sub" | "and" | "or" | "xor" | "sll" | "srl" | "sra" | "slt" | "sltu" => {
                Self::parse_r_type(mnemonic, tokens).map(Some)
            }
            // RV32I I-type instructions
            "addi" | "andi" | "ori" | "xori" | "slli" | "srli" | "srai" | "slti" | "sltiu" | "lw" | "lh"
            | "lb" | "lwu" | "lhu" | "lbu" | "jalr" => Self::parse_i_type(mnemonic, tokens).map(Some),
            // RV32I S-type instructions
            "sw" | "sh" | "sb" => Self::parse_s_type(mnemonic, tokens).map(Some),
            // RV32I B-type instructions
            "beq" | "bne" | "blt" | "bltu" | "bge" | "bgeu" => {
                Self::parse_b_type(mnemonic, tokens).map(Some)
            }
            // RV32I U-type instructions
            "lui" | "auipc" => Self::parse_u_type(mnemonic, tokens).map(Some),
            // RV32I J-type instructions
            "jal" => Self::parse_j_type(mnemonic, tokens).map(Some),
            // RV32F FR-type instructions
            "fadd.s" | "fsub.s" | "fmul.s" | "fdiv.s" | "fmin.s" | "fmax.s" => {
                Self::parse_f_r_type(mnemonic, tokens).map(Some)
            }
            // RV32F FI-type (load)
            "flw" => Self::parse_f_i_type(mnemonic, tokens).map(Some),
            // RV32F FS-type (store)
            "fsw" => Self::parse_f_s_type(mnemonic, tokens).map(Some),
            // RV32F FC-type (compare)
            "feq.s" | "flt.s" | "fle.s" => Self::parse_f_c_type(mnemonic, tokens).map(Some),
            // RV32F FCVT (int to float)
            "fcvt.s.w" => Self::parse_f_cvt_rev_type(mnemonic, tokens).map(Some),
            // RV32F FCVT (float to int)
            "fcvt.w.s" | "fcvt.wu.s" => Self::parse_f_cvt_type(mnemonic, tokens).map(Some),
            // RV32F FMV (float to int reg)
            "fmv.x.w" => Self::parse_f_move_type(mnemonic, tokens).map(Some),
            // RV32F FMV (int to float reg)
            "fmv.w.x" => Self::parse_f_move_rev_type(mnemonic, tokens).map(Some),
            // Neural custom ops v1 (0x77) and v2-preview (0x7B)
            "nmatvec.f32" | "nmatvecx.f32" | "nmatvec4x.f32" | "nmatvec8x.f32" => {
                Self::parse_n_desc_type(mnemonic, tokens).map(Some)
            }
            "nvrelu.f32" | "nvsigpwl.f32" | "nvclampu8.f32"
            | "nvrelux.f32" | "nvsigpwlx.f32" | "nvclampu8x.f32" => {
                Self::parse_n_vec_type(mnemonic, tokens).map(Some)
            }
            _ => Err(AssemblerError::UnknownInstruction(mnemonic)),
        }
    }


    fn parse_r_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        if tokens.len() != 6 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                3,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let rs1 = Self::expect_register(&tokens[3])?;
        Self::expect_comma(&tokens[4])?;
        let rs2 = Self::expect_register(&tokens[5])?;

        Ok(Instruction::RType {
            mnemonic,
            rd,
            rs1,
            rs2,
        })
    }

    fn parse_i_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        // Special handling for jalr memory form: jalr rd, imm(rs1)
        if mnemonic == "jalr" && tokens.len() == 7 {
            let rd = Self::expect_register(&tokens[1])?;
            Self::expect_comma(&tokens[2])?;
            let imm = Self::expect_integer(&tokens[3])?;
            Self::expect_lparen(&tokens[4])?;
            let rs1 = Self::expect_register(&tokens[5])?;
            Self::expect_rparen(&tokens[6])?;

            return Ok(Instruction::IType {
                mnemonic,
                rd,
                rs1,
                imm,
            });
        }

        // Special handling for regular load instructions with offset
        if mnemonic == "lw" || mnemonic == "lh" || mnemonic == "lb" || mnemonic == "lwu" 
            || mnemonic == "lhu" || mnemonic == "lbu" {
            // Format: lw rd, offset(rs1)
            // Tokens: [Mnemonic, Register, Comma, Integer, LeftParen, Register, RightParen]
            if tokens.len() != 7 {
                return Err(AssemblerError::WrongOperandCount(
                    mnemonic.clone(),
                    2,
                    tokens.len() - 1,
                ));
            }

            let rd = Self::expect_register(&tokens[1])?;
            Self::expect_comma(&tokens[2])?;
            let imm = Self::expect_integer(&tokens[3])?;
            Self::expect_lparen(&tokens[4])?;
            let rs1 = Self::expect_register(&tokens[5])?;
            Self::expect_rparen(&tokens[6])?;

            return Ok(Instruction::IType {
                mnemonic,
                rd,
                rs1,
                imm,
            });
        }

        // For regular I-type (e.g., addi x1, x0, 42)
        // Tokens: [Mnemonic, Register, Comma, Register, Comma, Integer]
        if tokens.len() != 6 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                3,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let rs1 = Self::expect_register(&tokens[3])?;
        Self::expect_comma(&tokens[4])?;
        let imm = Self::expect_integer(&tokens[5])?;

        Ok(Instruction::IType {
            mnemonic,
            rd,
            rs1,
            imm,
        })
    }

    fn parse_s_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        // Format: sw rs2, offset(rs1)
        // Tokens: [Mnemonic, Register, Comma, Integer, LeftParen, Register, RightParen]
        if tokens.len() != 7 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                2,
                tokens.len() - 1,
            ));
        }

        let rs2 = Self::expect_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let imm = Self::expect_integer(&tokens[3])?;
        Self::expect_lparen(&tokens[4])?;
        let rs1 = Self::expect_register(&tokens[5])?;
        Self::expect_rparen(&tokens[6])?;

        Ok(Instruction::SType {
            mnemonic,
            rs1,
            rs2,
            imm,
        })
    }

    fn parse_b_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        // Format: beq rs1, rs2, imm
        // Tokens: [Mnemonic, Register, Comma, Register, Comma, Integer]
        if tokens.len() != 6 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                3,
                tokens.len() - 1,
            ));
        }

        let rs1 = Self::expect_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let rs2 = Self::expect_register(&tokens[3])?;
        Self::expect_comma(&tokens[4])?;
        let imm = Self::expect_integer(&tokens[5])?;

        Ok(Instruction::BType {
            mnemonic,
            rs1,
            rs2,
            imm,
        })
    }

    fn parse_u_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        // Format: lui rd, imm
        // Tokens: [Mnemonic, Register, Comma, Integer]
        if tokens.len() != 4 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                2,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let imm = Self::expect_integer(&tokens[3])?;

        Ok(Instruction::UType {
            mnemonic,
            rd,
            imm,
        })
    }

    fn parse_j_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        // Format: jal rd, imm
        // Tokens: [Mnemonic, Register, Comma, Integer]
        if tokens.len() != 4 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                2,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let imm = Self::expect_integer(&tokens[3])?;

        Ok(Instruction::JType {
            mnemonic,
            rd,
            imm,
        })
    }

    fn parse_f_r_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        if tokens.len() != 6 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                3,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_float_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let rs1 = Self::expect_float_register(&tokens[3])?;
        Self::expect_comma(&tokens[4])?;
        let rs2 = Self::expect_float_register(&tokens[5])?;

        Ok(Instruction::FRType {
            mnemonic,
            rd,
            rs1,
            rs2,
        })
    }

    fn parse_f_i_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        if tokens.len() != 7 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                2,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_float_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let imm = Self::expect_integer(&tokens[3])?;
        Self::expect_lparen(&tokens[4])?;
        let rs1 = Self::expect_register(&tokens[5])?;
        Self::expect_rparen(&tokens[6])?;

        Ok(Instruction::FIType {
            mnemonic,
            rd,
            rs1,
            imm,
        })
    }

    fn parse_f_s_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        if tokens.len() != 7 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                2,
                tokens.len() - 1,
            ));
        }

        let rs2 = Self::expect_float_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let imm = Self::expect_integer(&tokens[3])?;
        Self::expect_lparen(&tokens[4])?;
        let rs1 = Self::expect_register(&tokens[5])?;
        Self::expect_rparen(&tokens[6])?;

        Ok(Instruction::FSType {
            mnemonic,
            rs1,
            rs2,
            imm,
        })
    }

    fn parse_f_c_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        if tokens.len() != 6 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                3,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let rs1 = Self::expect_float_register(&tokens[3])?;
        Self::expect_comma(&tokens[4])?;
        let rs2 = Self::expect_float_register(&tokens[5])?;

        Ok(Instruction::FCType {
            mnemonic,
            rd,
            rs1,
            rs2,
        })
    }

    fn parse_f_cvt_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        if tokens.len() != 4 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                2,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let rs1 = Self::expect_float_register(&tokens[3])?;

        Ok(Instruction::FCvtType {
            mnemonic,
            rd,
            rs1,
        })
    }

    fn parse_f_cvt_rev_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        if tokens.len() != 4 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                2,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_float_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let rs1 = Self::expect_register(&tokens[3])?;

        Ok(Instruction::FCvtRevType {
            mnemonic,
            rd,
            rs1,
        })
    }

    fn parse_f_move_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        if tokens.len() != 4 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                2,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let rs1 = Self::expect_float_register(&tokens[3])?;

        Ok(Instruction::FMoveType {
            mnemonic,
            rd,
            rs1,
        })
    }

    fn parse_f_move_rev_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        if tokens.len() != 4 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                2,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_float_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let rs1 = Self::expect_register(&tokens[3])?;

        Ok(Instruction::FMoveRevType {
            mnemonic,
            rd,
            rs1,
        })
    }

    fn parse_n_desc_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        // Format: nmatvec.f32 rd_status, rs_desc
        if tokens.len() != 4 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                2,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let rs1 = Self::expect_register(&tokens[3])?;

        Ok(Instruction::NType {
            mnemonic,
            rd,
            rs1,
            rs2: Register::X0,
            rs3: Register::X0,
        })
    }

    fn parse_n_vec_type(mnemonic: String, tokens: &[Token]) -> Result<Instruction> {
        // Format: nvrelu.f32 rd_status, rs_dst, rs_src, rs_len
        if tokens.len() != 8 {
            return Err(AssemblerError::WrongOperandCount(
                mnemonic.clone(),
                4,
                tokens.len() - 1,
            ));
        }

        let rd = Self::expect_register(&tokens[1])?;
        Self::expect_comma(&tokens[2])?;
        let rs1 = Self::expect_register(&tokens[3])?;
        Self::expect_comma(&tokens[4])?;
        let rs2 = Self::expect_register(&tokens[5])?;
        Self::expect_comma(&tokens[6])?;
        let rs3 = Self::expect_register(&tokens[7])?;

        Ok(Instruction::NType {
            mnemonic,
            rd,
            rs1,
            rs2,
            rs3,
        })
    }

    // Helper methods
    fn expect_register(token: &Token) -> Result<Register> {
        match token {
            Token::Register(name) => {
                Register::from_name(name).ok_or_else(|| {
                    AssemblerError::InvalidRegister(name.clone())
                })
            }
            Token::Mnemonic(name) => {
                // Handle pseudo-register names like t0, a0, s0, sp, etc.
                // These are valid register names but might be tokenized as mnemonics
                Register::from_name(name).ok_or_else(|| {
                    AssemblerError::InvalidOperand(format!(
                        "expected register, got mnemonic({})",
                        name
                    ))
                })
            }
            _ => Err(AssemblerError::InvalidOperand(format!(
                "expected register, got {}",
                token
            ))),
        }
    }

    fn expect_float_register(token: &Token) -> Result<FloatRegister> {
        match token {
            Token::FloatRegister(name) => {
                FloatRegister::from_name(name).ok_or_else(|| {
                    AssemblerError::InvalidRegister(name.clone())
                })
            }
            Token::Mnemonic(name) => {
                // Handle pseudo-register names
                FloatRegister::from_name(name).ok_or_else(|| {
                    AssemblerError::InvalidOperand(format!(
                        "expected float register, got mnemonic({})",
                        name
                    ))
                })
            }
            _ => Err(AssemblerError::InvalidOperand(format!(
                "expected float register, got {}",
                token
            ))),
        }
    }

    fn expect_integer(token: &Token) -> Result<i64> {
        match token {
            Token::Integer(i) => Ok(*i),
            _ => Err(AssemblerError::InvalidOperand(format!(
                "expected integer, got {}",
                token
            ))),
        }
    }

    fn expect_comma(token: &Token) -> Result<()> {
        match token {
            Token::Comma => Ok(()),
            _ => Err(AssemblerError::InvalidOperand(format!(
                "expected comma, got {}",
                token
            ))),
        }
    }

    fn expect_lparen(token: &Token) -> Result<()> {
        match token {
            Token::LeftParen => Ok(()),
            _ => Err(AssemblerError::InvalidOperand(format!(
                "expected '(', got {}",
                token
            ))),
        }
    }

    fn expect_rparen(token: &Token) -> Result<()> {
        match token {
            Token::RightParen => Ok(()),
            _ => Err(AssemblerError::InvalidOperand(format!(
                "expected ')', got {}",
                token
            ))),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_add() {
        let tokens = crate::lexer::tokenize("add x1, x2, x3").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::RType { mnemonic, rd, rs1, rs2 }) => {
                assert_eq!(mnemonic, "add");
                assert_eq!(rd, Register::X1);
                assert_eq!(rs1, Register::X2);
                assert_eq!(rs2, Register::X3);
            }
            _ => panic!("expected RType"),
        }
    }

    #[test]
    fn test_parse_addi() {
        let tokens = crate::lexer::tokenize("addi x1, x0, 42").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::IType { mnemonic, rd, rs1, imm }) => {
                assert_eq!(mnemonic, "addi");
                assert_eq!(rd, Register::X1);
                assert_eq!(rs1, Register::X0);
                assert_eq!(imm, 42);
            }
            _ => panic!("expected IType"),
        }
    }

    #[test]
    fn test_parse_lw() {
        let tokens = crate::lexer::tokenize("lw x1, 4(x2)").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::IType { mnemonic, rd, rs1, imm }) => {
                assert_eq!(mnemonic, "lw");
                assert_eq!(rd, Register::X1);
                assert_eq!(rs1, Register::X2);
                assert_eq!(imm, 4);
            }
            _ => panic!("expected IType"),
        }
    }

    #[test]
    fn test_parse_fadd_s() {
        let tokens = crate::lexer::tokenize("fadd.s f1, f2, f3").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::FRType { mnemonic, rd, rs1, rs2 }) => {
                assert_eq!(mnemonic, "fadd.s");
                assert_eq!(rd, FloatRegister::F1);
                assert_eq!(rs1, FloatRegister::F2);
                assert_eq!(rs2, FloatRegister::F3);
            }
            _ => panic!("expected FRType"),
        }
    }

    #[test]
    fn test_parse_jalr_memory_form() {
        let tokens = crate::lexer::tokenize("jalr ra, 0(t0)").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::IType { mnemonic, rd, rs1, imm }) => {
                assert_eq!(mnemonic, "jalr");
                assert_eq!(rd, Register::X1);
                assert_eq!(rs1, Register::X5);
                assert_eq!(imm, 0);
            }
            _ => panic!("expected IType"),
        }
    }

    #[test]
    fn test_parse_flw_offset_form() {
        let tokens = crate::lexer::tokenize("flw f1, 0(t0)").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::FIType { mnemonic, rd, rs1, imm }) => {
                assert_eq!(mnemonic, "flw");
                assert_eq!(rd, FloatRegister::F1);
                assert_eq!(rs1, Register::X5);
                assert_eq!(imm, 0);
            }
            _ => panic!("expected FIType"),
        }
    }

    #[test]
    fn test_parse_feq_s() {
        let tokens = crate::lexer::tokenize("feq.s x11, f1, f2").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::FCType { mnemonic, rd, rs1, rs2 }) => {
                assert_eq!(mnemonic, "feq.s");
                assert_eq!(rd, Register::X11);
                assert_eq!(rs1, FloatRegister::F1);
                assert_eq!(rs2, FloatRegister::F2);
            }
            _ => panic!("expected FCType"),
        }
    }

    #[test]
    fn test_parse_fmv_aliases() {
        let tokens = crate::lexer::tokenize("fmv.s.x fa0, x0").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();
        match instr {
            Some(Instruction::FMoveRevType { mnemonic, rd, rs1 }) => {
                assert_eq!(mnemonic, "fmv.w.x");
                assert_eq!(rd, FloatRegister::F10);
                assert_eq!(rs1, Register::X0);
            }
            _ => panic!("expected FMoveRevType"),
        }

        let tokens = crate::lexer::tokenize("fmv.x.s a0, fa5").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();
        match instr {
            Some(Instruction::FMoveType { mnemonic, rd, rs1 }) => {
                assert_eq!(mnemonic, "fmv.x.w");
                assert_eq!(rd, Register::X10);
                assert_eq!(rs1, FloatRegister::F15);
            }
            _ => panic!("expected FMoveType"),
        }
    }

    #[test]
    fn test_parse_fcvt_wu_s() {
        let tokens = crate::lexer::tokenize("fcvt.wu.s t5, fa0").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::FCvtType { mnemonic, rd, rs1 }) => {
                assert_eq!(mnemonic, "fcvt.wu.s");
                assert_eq!(rd, Register::X30);
                assert_eq!(rs1, FloatRegister::F10);
            }
            _ => panic!("expected FCvtType"),
        }
    }

    #[test]
    fn test_parse_nmatvec_f32() {
        let tokens = crate::lexer::tokenize("NMATVEC.F32 t1, t0").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::NType {
                mnemonic,
                rd,
                rs1,
                rs2,
                rs3,
            }) => {
                assert_eq!(mnemonic, "nmatvec.f32");
                assert_eq!(rd, Register::X6);
                assert_eq!(rs1, Register::X5);
                assert_eq!(rs2, Register::X0);
                assert_eq!(rs3, Register::X0);
            }
            _ => panic!("expected NType"),
        }
    }

    #[test]
    fn test_parse_nvrelu_f32() {
        let tokens = crate::lexer::tokenize("NVRELU.F32 a0, a1, a2, a3").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::NType {
                mnemonic,
                rd,
                rs1,
                rs2,
                rs3,
            }) => {
                assert_eq!(mnemonic, "nvrelu.f32");
                assert_eq!(rd, Register::X10);
                assert_eq!(rs1, Register::X11);
                assert_eq!(rs2, Register::X12);
                assert_eq!(rs3, Register::X13);
            }
            _ => panic!("expected NType"),
        }
    }

    #[test]
    fn test_parse_nvsigpwl_f32() {
        let tokens = crate::lexer::tokenize("NVSIGPWL.F32 t0, s2, s2, s3").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::NType {
                mnemonic,
                rd,
                rs1,
                rs2,
                rs3,
            }) => {
                assert_eq!(mnemonic, "nvsigpwl.f32");
                assert_eq!(rd, Register::X5);
                assert_eq!(rs1, Register::X18);
                assert_eq!(rs2, Register::X18);
                assert_eq!(rs3, Register::X19);
            }
            _ => panic!("expected NType"),
        }
    }

    #[test]
    fn test_parse_nvclampu8_f32() {
        let tokens = crate::lexer::tokenize("NVCLAMPU8.F32 t0, a0, a1, a2").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::NType {
                mnemonic,
                rd,
                rs1,
                rs2,
                rs3,
            }) => {
                assert_eq!(mnemonic, "nvclampu8.f32");
                assert_eq!(rd, Register::X5);
                assert_eq!(rs1, Register::X10);
                assert_eq!(rs2, Register::X11);
                assert_eq!(rs3, Register::X12);
            }
            _ => panic!("expected NType"),
        }
    }

    #[test]
    fn test_parse_nmatvecx_f32() {
        let tokens = crate::lexer::tokenize("NMATVECX.F32 t1, t0").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::NType {
                mnemonic,
                rd,
                rs1,
                rs2,
                rs3,
            }) => {
                assert_eq!(mnemonic, "nmatvecx.f32");
                assert_eq!(rd, Register::X6);
                assert_eq!(rs1, Register::X5);
                assert_eq!(rs2, Register::X0);
                assert_eq!(rs3, Register::X0);
            }
            _ => panic!("expected NType"),
        }
    }

    #[test]
    fn test_parse_nmatvec4x_f32() {
        let tokens = crate::lexer::tokenize("NMATVEC4X.F32 t1, t0").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::NType {
                mnemonic,
                rd,
                rs1,
                rs2,
                rs3,
            }) => {
                assert_eq!(mnemonic, "nmatvec4x.f32");
                assert_eq!(rd, Register::X6);
                assert_eq!(rs1, Register::X5);
                assert_eq!(rs2, Register::X0);
                assert_eq!(rs3, Register::X0);
            }
            _ => panic!("expected NType"),
        }
    }

    #[test]
    fn test_parse_nmatvec8x_f32() {
        let tokens = crate::lexer::tokenize("NMATVEC8X.F32 t1, t0").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::NType {
                mnemonic,
                rd,
                rs1,
                rs2,
                rs3,
            }) => {
                assert_eq!(mnemonic, "nmatvec8x.f32");
                assert_eq!(rd, Register::X6);
                assert_eq!(rs1, Register::X5);
                assert_eq!(rs2, Register::X0);
                assert_eq!(rs3, Register::X0);
            }
            _ => panic!("expected NType"),
        }
    }

    #[test]
    fn test_parse_nvrelux_f32() {
        let tokens = crate::lexer::tokenize("NVRELUX.F32 a0, a1, a2, a3").unwrap();
        let instr = Parser::parse_instruction(&tokens).unwrap();

        match instr {
            Some(Instruction::NType {
                mnemonic,
                rd,
                rs1,
                rs2,
                rs3,
            }) => {
                assert_eq!(mnemonic, "nvrelux.f32");
                assert_eq!(rd, Register::X10);
                assert_eq!(rs1, Register::X11);
                assert_eq!(rs2, Register::X12);
                assert_eq!(rs3, Register::X13);
            }
            _ => panic!("expected NType"),
        }
    }
}

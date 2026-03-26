//! RV32 Assembler Library - Phase D.1 Foundation
//!
//! Scope: RV32I + RV32F instruction encoding with directives and pseudo-instructions.
//! Outputs raw 32-bit instruction words in little-endian order.

pub mod error;
pub mod instruction;
pub mod lexer;
pub mod parser;
pub mod encoder;

pub use error::{AssemblerError, Result};
pub use parser::Parser;
pub use encoder::Encoder;
pub use lexer::Token;

/// Assemble a single line of RISC-V assembly.
/// Returns the encoded 32-bit instruction as 4 bytes (little-endian).
/// Returns None if the line is a directive, label, or other non-instruction.
pub fn assemble_instruction(line: &str) -> Result<Option<[u8; 4]>> {
    let tokens = lexer::tokenize(line)?;
    if let Some(instruction) = Parser::parse_instruction(&tokens)? {
        let encoded = Encoder::encode(&instruction)?;
        Ok(Some(encoded))
    } else {
        Ok(None)
    }
}

/// Assemble multiple lines of assembly code.
/// Returns bytes in order, expanding pseudo-instructions as needed.
pub fn assemble_program(text: &str) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();

    for line in text.lines() {
        let trimmed = line.trim();

        // Skip empty lines and comments
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }

        // Trim comments from end of line
        let line_without_comment = if let Some(comment_pos) = trimmed.find('#') {
            trimmed[..comment_pos].trim()
        } else {
            trimmed
        };

        if line_without_comment.is_empty() {
            continue;
        }

        // Assemble line - may produce multiple instructions
        let words = assemble_line(line_without_comment)?;
        for word in words {
            bytes.extend_from_slice(&word);
        }
    }

    Ok(bytes)
}

/// Assemble a line of code, returning zero or more 32-bit instructions
fn assemble_line(line: &str) -> Result<Vec<[u8; 4]>> {
    let tokens = lexer::tokenize(line)?;
    
    if tokens.is_empty() {
        return Ok(Vec::new());
    }

    // Check if this is a li pseudo-instruction
    if let Some(Token::Mnemonic(mnemonic)) = tokens.first() {
        if mnemonic == "li" && tokens.len() == 4 {
            // li rd, imm - may expand to lui + addi
            if let (Token::Mnemonic(rd_name), Token::Comma, Token::Integer(imm)) =
                (&tokens[1], &tokens[2], &tokens[3])
            {
                use instruction::Register;
                if let Some(rd) = Register::from_name(rd_name) {
                    return expand_li(rd, *imm);
                }
            }
        } else if mnemonic == "la" && tokens.len() == 4 {
            // la rd, symbol - expands to auipc + addi
            // Without symbol resolution, we can't compute the offset, so we emit auipc + addi with imm=0
            if let (Token::Mnemonic(rd_name), Token::Comma, Token::Mnemonic(_symbol)) =
                (&tokens[1], &tokens[2], &tokens[3])
            {
                use instruction::Register;
                if let Some(rd) = Register::from_name(rd_name) {
                    return expand_la(rd);
                }
            }
        }
    }

    // Regular instruction
    if let Some(instruction) = Parser::parse_instruction(&tokens)? {
        let encoded = Encoder::encode(&instruction)?;
        Ok(vec![encoded])
    } else {
        Ok(Vec::new())
    }
}

/// Expand la (load address) pseudo-instruction
fn expand_la(rd: instruction::Register) -> Result<Vec<[u8; 4]>> {
    use instruction::Instruction;
    
    let mut result = Vec::new();
    
    // la rd, symbol → auipc rd, %pcrel_hi(symbol)
    //             → addi rd, rd, %pcrel_lo(symbol)
    // Without a symbol table, we emit with immediate = 0
    
    // Emit auipc
    let auipc_instr = Instruction::UType {
        mnemonic: "auipc".to_string(),
        rd,
        imm: 0,
    };
    result.push(Encoder::encode(&auipc_instr)?);
    
    // Emit addi
    let addi_instr = Instruction::IType {
        mnemonic: "addi".to_string(),
        rd,
        rs1: rd,
        imm: 0,
    };
    result.push(Encoder::encode(&addi_instr)?);
    
    Ok(result)
}

fn expand_li(rd: instruction::Register, imm: i64) -> Result<Vec<[u8; 4]>> {
    use instruction::Instruction;
    
    let mut result = Vec::new();
    
    if imm >= -2048 && imm <= 2047 {
        // Fits in 12 bits, single addi
        let instr = Instruction::IType {
            mnemonic: "addi".to_string(),
            rd,
            rs1: instruction::Register::X0,
            imm,
        };
        result.push(Encoder::encode(&instr)?);
    } else {
        // Need lui + addi
        // Split imm into upper 20 bits and lower 12 bits (sign-extended)
        let upper = ((imm >> 12) + ((imm & 0x800) >> 11)) & 0xFFFFF;  // lui immediate
        let lower = (imm & 0xFFF) as i64;
        let lower_signed = if lower & 0x800 != 0 {
            lower as i32 as i64  // Sign-extend 12 bits
        } else {
            lower
        };
        
        // Emit lui
        let lui_instr = Instruction::UType {
            mnemonic: "lui".to_string(),
            rd,
            imm: upper as i64,
        };
        result.push(Encoder::encode(&lui_instr)?);
        
        // Emit addi
        let addi_instr = Instruction::IType {
            mnemonic: "addi".to_string(),
            rd,
            rs1: rd,
            imm: lower_signed,
        };
        result.push(Encoder::encode(&addi_instr)?);
    }
    
    Ok(result)
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simple_addi() {
        // addi x1, x0, 42
        let result = assemble_instruction("addi x1, x0, 42");
        assert!(result.is_ok());

        let bytes = result.unwrap();
        // Verify it's 4 bytes
        assert_eq!(bytes.len(), 4);
    }

    #[test]
    fn test_program_with_comments() {
        let program = r#"
            # Load 42 into x1
            addi x1, x0, 42
            
            # Add 10 to x1
            addi x1, x1, 10
        "#;

        let result = assemble_program(program);
        assert!(result.is_ok());
        assert_eq!(result.unwrap().len(), 8); // 2 instructions
    }
}


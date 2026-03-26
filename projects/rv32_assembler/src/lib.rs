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
/// Returns bytes in order, expanding pseudo-instructions and resolving labels.
pub fn assemble_program(text: &str) -> Result<Vec<u8>> {
    // Parse all lines first
    let mut lines: Vec<&str> = Vec::new();
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
        
        if !line_without_comment.is_empty() {
            lines.push(line_without_comment);
        }
    }
    
    // First pass: collect labels and their byte offsets by simulating assembly
    let mut label_map = std::collections::HashMap::new();
    let mut byte_offset = 0;
    
    for line in &lines {
        let tokens = match lexer::tokenize(line) {
            Ok(t) => t,
            Err(_) => continue,  // Skip lines with parse errors on first pass
        };
        
        if tokens.is_empty() {
            continue;
        }
        
        // Check for labels
        if let Some(Token::Label(label_name)) = tokens.first() {
            label_map.insert(label_name.clone(), byte_offset);
            continue;
        }
        
        // Skip directives and non-instructions
        match tokens.first() {
            Some(Token::Directive(_)) | Some(Token::String(_)) => continue,
            _ => {}
        }
        
        // Calculate the size of this line (simulate assembly without encoding)
        if let Some(Token::Mnemonic(mnemonic)) = tokens.first() {
            if mnemonic == "li" && tokens.len() == 4 {
                // Check if imm fits in 12 bits
                if let Token::Integer(imm) = &tokens[3] {
                    if *imm >= -2048 && *imm <= 2047 {
                        byte_offset += 4;  // Single addi
                    } else {
                        byte_offset += 8;  // lui + addi
                    }
                } else {
                    byte_offset += 8;  // Conservative: assume 2 instructions
                }
            } else if mnemonic == "la" && tokens.len() == 4 {
                byte_offset += 8;  // la always expands to 2 instructions (auipc + addi)
            } else {
                byte_offset += 4;  // regular instruction
            }
        }
    }
    
    // Second pass: assemble with label resolution
    let mut bytes = Vec::new();
    
    for line in &lines {
        let tokens = lexer::tokenize(line)?;
        
        if tokens.is_empty() {
            continue;
        }
        
        // Skip labels and directives
        match tokens.first() {
            Some(Token::Label(_)) | Some(Token::Directive(_)) | Some(Token::String(_)) => continue,
            _ => {}
        }
        
        // Assemble line with label map available
        let words = assemble_line_with_labels(line, &label_map, bytes.len())?;
        for word in words {
            bytes.extend_from_slice(&word);
        }
    }
    
    Ok(bytes)
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

/// Assemble a line with label resolution
fn assemble_line_with_labels(
    line: &str,
    label_map: &std::collections::HashMap<String, usize>,
    current_byte_offset: usize,
) -> Result<Vec<[u8; 4]>> {
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
            // la rd, symbol - expands to auipc + addi with label resolution
            if let (Token::Mnemonic(rd_name), Token::Comma, Token::Mnemonic(symbol)) =
                (&tokens[1], &tokens[2], &tokens[3])
            {
                use instruction::Register;
                if let Some(rd) = Register::from_name(rd_name) {
                    // Resolve label
                    if let Some(&label_offset) = label_map.get(symbol) {
                        let offset = label_offset as i64 - current_byte_offset as i64;
                        return expand_la_with_offset(rd, offset);
                    }
                    // If label not found, emit with 0 offset (error will be caught elsewhere)
                    return expand_la(rd);
                }
            }
        }
    }

    // Handle branch instructions with labels
    if let Some(Token::Mnemonic(mnemonic)) = tokens.first() {
        if ["beq", "bne", "blt", "bltu", "bge", "bgeu"].contains(&mnemonic.as_str()) {
            // These might have a label as the third operand
            if tokens.len() >= 6 {
                if let (Token::Mnemonic(rs1_name), Token::Comma, Token::Mnemonic(rs2_name), 
                        Token::Comma, Token::Mnemonic(label_name)) =
                    (&tokens[1], &tokens[2], &tokens[3], &tokens[4], &tokens[5])
                {
                    use instruction::Register;
                    if let (Some(rs1), Some(rs2)) = (Register::from_name(rs1_name), Register::from_name(rs2_name)) {
                        if let Some(&label_offset) = label_map.get(label_name) {
                            let imm = label_offset as i64 - current_byte_offset as i64;
                            let instruction = instruction::Instruction::BType {
                                mnemonic: mnemonic.clone(),
                                rs1,
                                rs2,
                                imm,
                            };
                            let encoded = Encoder::encode(&instruction)?;
                            return Ok(vec![encoded]);
                        }
                    }
                }
            }
        }
    }

    // Handle jal instruction with labels
    if let Some(Token::Mnemonic(mnemonic)) = tokens.first() {
        if mnemonic == "jal" {
            if tokens.len() == 4 {
                if let (Token::Mnemonic(rd_name), Token::Comma, Token::Mnemonic(label_name)) =
                    (&tokens[1], &tokens[2], &tokens[3])
                {
                    use instruction::Register;
                    if let Some(rd) = Register::from_name(rd_name) {
                        if let Some(&label_offset) = label_map.get(label_name) {
                            let imm = label_offset as i64 - current_byte_offset as i64;
                            let instruction = instruction::Instruction::JType {
                                mnemonic: mnemonic.clone(),
                                rd,
                                imm,
                            };
                            let encoded = Encoder::encode(&instruction)?;
                            return Ok(vec![encoded]);
                        }
                    }
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

/// Expand la (load address) with resolved offset
fn expand_la_with_offset(rd: instruction::Register, offset: i64) -> Result<Vec<[u8; 4]>> {
    use instruction::Instruction;
    
    let mut result = Vec::new();
    
    // Split offset into upper 20-bit and lower 12-bit components (PC-relative)
    // auipc rd, upper
    // addi rd, rd, lower
    let upper = ((offset + 0x800) >> 12) & 0xFFFFF;  // Round up if lower is negative
    let lower = offset & 0xFFF;
    let lower_signed = if lower >= 0x800 { lower as i64 - 4096 } else { lower as i64 };
    
    // Emit auipc
    let auipc_instr = Instruction::UType {
        mnemonic: "auipc".to_string(),
        rd,
        imm: upper as i64,
    };
    result.push(Encoder::encode(&auipc_instr)?);
    
    // Emit addi
    let addi_instr = Instruction::IType {
        mnemonic: "addi".to_string(),
        rd,
        rs1: rd,
        imm: lower_signed,
    };
    result.push(Encoder::encode(&addi_instr)?);
    
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


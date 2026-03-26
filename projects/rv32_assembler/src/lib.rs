//! RV32 Assembler Library - Phase C Foundation
//!
//! Minimal scope: RV32I + RV32F instruction encoding.
//! No labels, symbols, directives, or linker.
//! Outputs raw 32-bit instruction words in little-endian order.

pub mod error;
pub mod instruction;
pub mod lexer;
pub mod parser;
pub mod encoder;

pub use error::{AssemblerError, Result};
pub use parser::Parser;
pub use encoder::Encoder;

/// Assemble a single line of RISC-V assembly.
/// Returns the encoded 32-bit instruction as 4 bytes (little-endian).
pub fn assemble_instruction(line: &str) -> Result<[u8; 4]> {
    let tokens = lexer::tokenize(line)?;
    let instruction = Parser::parse_instruction(&tokens)?;
    let encoded = Encoder::encode(&instruction)?;
    Ok(encoded)
}

/// Assemble multiple lines of assembly code.
/// Returns bytes in order, one 32-bit word per line.
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

        let word = assemble_instruction(line_without_comment)?;
        bytes.extend_from_slice(&word);
    }

    Ok(bytes)
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


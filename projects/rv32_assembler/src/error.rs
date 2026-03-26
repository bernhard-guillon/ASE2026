//! Error types for assembler

use thiserror::Error;

pub type Result<T> = std::result::Result<T, AssemblerError>;

#[derive(Debug, Error)]
pub enum AssemblerError {
    #[error("Lexer error: {0}")]
    LexerError(String),

    #[error("Parser error: {0}")]
    ParserError(String),

    #[error("Encoder error: {0}")]
    EncoderError(String),

    #[error("Unknown instruction: {0}")]
    UnknownInstruction(String),

    #[error("Invalid register: {0}")]
    InvalidRegister(String),

    #[error("Invalid immediate value: {0} (out of range for {1})")]
    InvalidImmediate(i64, String),

    #[error("Wrong number of operands for {0}: expected {1}, got {2}")]
    WrongOperandCount(String, usize, usize),

    #[error("Invalid operand: {0}")]
    InvalidOperand(String),
}

//! Lexer: tokenize assembly input

use crate::error::{AssemblerError, Result};

#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    Mnemonic(String),
    Register(String),
    FloatRegister(String),
    Integer(i64),
    Comma,
    LeftParen,
    RightParen,
}

impl std::fmt::Display for Token {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Token::Mnemonic(s) => write!(f, "mnemonic({})", s),
            Token::Register(s) => write!(f, "register({})", s),
            Token::FloatRegister(s) => write!(f, "float_register({})", s),
            Token::Integer(i) => write!(f, "int({})", i),
            Token::Comma => write!(f, "comma"),
            Token::LeftParen => write!(f, "lparen"),
            Token::RightParen => write!(f, "rparen"),
        }
    }
}

/// Tokenize a line of assembly
pub fn tokenize(line: &str) -> Result<Vec<Token>> {
    let mut tokens = Vec::new();
    let mut chars = line.chars().peekable();

    while let Some(&ch) = chars.peek() {
        match ch {
            ' ' | '\t' | '\r' => {
                chars.next();
            }
            ',' => {
                tokens.push(Token::Comma);
                chars.next();
            }
            '(' => {
                tokens.push(Token::LeftParen);
                chars.next();
            }
            ')' => {
                tokens.push(Token::RightParen);
                chars.next();
            }
            '-' | '+' | '0'..='9' => {
                tokens.push(parse_integer(&mut chars)?);
            }
            'x' | 'X' => {
                // Check if this is a register (x followed by digit) or a mnemonic (xor, etc.)
                if let Some(next) = chars.clone().nth(1) {
                    if next.is_ascii_digit() {
                        let reg = parse_register(&mut chars)?;
                        tokens.push(reg);
                    } else {
                        let mnemonic = parse_mnemonic(&mut chars)?;
                        tokens.push(mnemonic);
                    }
                } else {
                    let mnemonic = parse_mnemonic(&mut chars)?;
                    tokens.push(mnemonic);
                }
            }
            'f' | 'F' => {
                if let Some(next) = chars.clone().nth(1) {
                    if next.is_ascii_digit() {
                        let freg = parse_float_register(&mut chars)?;
                        tokens.push(freg);
                    } else {
                        let mnemonic = parse_mnemonic(&mut chars)?;
                        tokens.push(mnemonic);
                    }
                } else {
                    let mnemonic = parse_mnemonic(&mut chars)?;
                    tokens.push(mnemonic);
                }
            }
            'a'..='z' | 'A'..='Z' | '_' => {
                let mnemonic = parse_mnemonic(&mut chars)?;
                tokens.push(mnemonic);
            }
            _ => {
                return Err(AssemblerError::LexerError(format!(
                    "unexpected character: '{}'",
                    ch
                )));
            }
        }
    }

    Ok(tokens)
}

fn parse_register(chars: &mut std::iter::Peekable<std::str::Chars>) -> Result<Token> {
    let mut name = String::new();
    name.push(chars.next().unwrap()); // 'x'

    while let Some(&ch) = chars.peek() {
        if ch.is_ascii_digit() {
            name.push(chars.next().unwrap());
        } else {
            break;
        }
    }

    Ok(Token::Register(name))
}

fn parse_float_register(chars: &mut std::iter::Peekable<std::str::Chars>) -> Result<Token> {
    let mut name = String::new();
    name.push(chars.next().unwrap()); // 'f'

    while let Some(&ch) = chars.peek() {
        if ch.is_ascii_digit() {
            name.push(chars.next().unwrap());
        } else {
            break;
        }
    }

    Ok(Token::FloatRegister(name))
}

fn parse_integer(chars: &mut std::iter::Peekable<std::str::Chars>) -> Result<Token> {
    let mut num_str = String::new();

    // Handle optional sign
    if let Some(&ch) = chars.peek() {
        if ch == '+' || ch == '-' {
            num_str.push(chars.next().unwrap());
        }
    }

    // Collect digits
    while let Some(&ch) = chars.peek() {
        if ch.is_ascii_digit() {
            num_str.push(chars.next().unwrap());
        } else {
            break;
        }
    }

    let value = num_str
        .parse::<i64>()
        .map_err(|_| AssemblerError::LexerError(format!("invalid integer: {}", num_str)))?;

    Ok(Token::Integer(value))
}

fn parse_mnemonic(chars: &mut std::iter::Peekable<std::str::Chars>) -> Result<Token> {
    let mut name = String::new();

    while let Some(&ch) = chars.peek() {
        if ch.is_ascii_alphanumeric() || ch == '_' || ch == '.' {
            name.push(chars.next().unwrap());
        } else {
            break;
        }
    }

    Ok(Token::Mnemonic(name.to_lowercase()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tokenize_simple_instruction() {
        let tokens = tokenize("addi x1, x0, 42").unwrap();
        // Tokens: Mnemonic, Register, Comma, Register, Comma, Integer
        assert_eq!(tokens.len(), 6);
        assert_eq!(tokens[0], Token::Mnemonic("addi".to_string()));
        assert_eq!(tokens[1], Token::Register("x1".to_string()));
        assert_eq!(tokens[2], Token::Comma);
        assert_eq!(tokens[3], Token::Register("x0".to_string()));
        assert_eq!(tokens[4], Token::Comma);
        assert_eq!(tokens[5], Token::Integer(42));
    }

    #[test]
    fn test_tokenize_with_negative_immediate() {
        let tokens = tokenize("addi x1, x1, -10").unwrap();
        assert_eq!(tokens[5], Token::Integer(-10));
    }

    #[test]
    fn test_tokenize_float_instruction() {
        let tokens = tokenize("fadd.s f1, f2, f3").unwrap();
        assert_eq!(tokens[0], Token::Mnemonic("fadd.s".to_string()));
        assert_eq!(tokens[1], Token::FloatRegister("f1".to_string()));
        assert_eq!(tokens[2], Token::Comma);
        assert_eq!(tokens[3], Token::FloatRegister("f2".to_string()));
    }

    #[test]
    fn test_tokenize_with_parens() {
        let tokens = tokenize("lw x1, 4(x2)").unwrap();
        // Tokens: Mnemonic, Register, Comma, Integer, LeftParen, Register, RightParen
        assert_eq!(tokens[3], Token::Integer(4));
        assert_eq!(tokens[4], Token::LeftParen);
        assert_eq!(tokens[5], Token::Register("x2".to_string()));
        assert_eq!(tokens[6], Token::RightParen);
    }
}

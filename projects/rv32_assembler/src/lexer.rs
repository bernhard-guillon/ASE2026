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
    Directive(String),  // .section, .globl, .data, .text, etc.
    Label(String),      // labels ending with :
    String(String),     // string literals
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
            Token::Directive(s) => write!(f, "directive({})", s),
            Token::Label(s) => write!(f, "label({})", s),
            Token::String(s) => write!(f, "string({})", s),
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
            '"' => {
                let string_lit = parse_string_literal(&mut chars)?;
                tokens.push(string_lit);
            }
            '.' => {
                let directive = parse_directive(&mut chars)?;
                // Allow local labels like `.Lfoo:` in addition to directives.
                if let Some(&':') = chars.peek() {
                    chars.next(); // consume ':'
                    if let Token::Directive(name) = directive {
                        tokens.push(Token::Label(name));
                    }
                } else {
                    tokens.push(directive);
                }
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
                        let word = parse_mnemonic_word(&mut chars)?;
                        // Check if it's a label (ends with ':')
                        if let Some(&':') = chars.peek() {
                            chars.next(); // consume ':'
                            tokens.push(Token::Label(word));
                        } else {
                            tokens.push(Token::Mnemonic(word));
                        }
                    }
                } else {
                    let word = parse_mnemonic_word(&mut chars)?;
                    // Check if it's a label (ends with ':')
                    if let Some(&':') = chars.peek() {
                        chars.next(); // consume ':'
                        tokens.push(Token::Label(word));
                    } else {
                        tokens.push(Token::Mnemonic(word));
                    }
                }
            }
            'a'..='z' | 'A'..='Z' | '_' => {
                let word = parse_identifier(&mut chars)?;
                // Check if it's a label (ends with ':')
                if let Some(&':') = chars.peek() {
                    chars.next(); // consume ':'
                    tokens.push(Token::Label(word));
                } else {
                    // It's a mnemonic
                    tokens.push(Token::Mnemonic(word));
                }
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
    let mut is_hex = false;
    let mut is_binary = false;

    // Handle optional sign
    if let Some(&ch) = chars.peek() {
        if ch == '+' || ch == '-' {
            num_str.push(chars.next().unwrap());
        }
    }

    // Check for hex (0x...) or binary (0b...)
    if let Some(&'0') = chars.peek() {
        num_str.push(chars.next().unwrap()); // consume '0'
        
        if let Some(&next_ch) = chars.peek() {
            match next_ch {
                'x' | 'X' => {
                    // Hexadecimal
                    num_str.clear(); // remove the leading '0'
                    chars.next(); // consume 'x' or 'X'
                    is_hex = true;
                    while let Some(&ch) = chars.peek() {
                        if ch.is_ascii_hexdigit() {
                            num_str.push(chars.next().unwrap());
                        } else {
                            break;
                        }
                    }
                }
                'b' | 'B' => {
                    // Binary
                    num_str.clear(); // remove the leading '0'
                    chars.next(); // consume 'b' or 'B'
                    is_binary = true;
                    while let Some(&ch) = chars.peek() {
                        if ch == '0' || ch == '1' {
                            num_str.push(chars.next().unwrap());
                        } else {
                            break;
                        }
                    }
                }
                _ => {
                    // Decimal, continue parsing
                    while let Some(&ch) = chars.peek() {
                        if ch.is_ascii_digit() {
                            num_str.push(chars.next().unwrap());
                        } else {
                            break;
                        }
                    }
                }
            }
        }
    } else {
        // Regular decimal
        while let Some(&ch) = chars.peek() {
            if ch.is_ascii_digit() {
                num_str.push(chars.next().unwrap());
            } else {
                break;
            }
        }
    }

    let value = if is_hex {
        i64::from_str_radix(&num_str, 16)
            .map_err(|_| AssemblerError::LexerError(format!("invalid hex integer: 0x{}", num_str)))?
    } else if is_binary {
        i64::from_str_radix(&num_str, 2)
            .map_err(|_| AssemblerError::LexerError(format!("invalid binary integer: 0b{}", num_str)))?
    } else {
        num_str
            .parse::<i64>()
            .map_err(|_| AssemblerError::LexerError(format!("invalid integer: {}", num_str)))?
    };

    Ok(Token::Integer(value))
}

fn parse_mnemonic(chars: &mut std::iter::Peekable<std::str::Chars>) -> Result<Token> {
    let word = parse_mnemonic_word(chars)?;
    Ok(Token::Mnemonic(word))
}

fn parse_mnemonic_word(chars: &mut std::iter::Peekable<std::str::Chars>) -> Result<String> {
    let mut name = String::new();

    while let Some(&ch) = chars.peek() {
        if ch.is_ascii_alphanumeric() || ch == '_' || ch == '.' {
            name.push(chars.next().unwrap());
        } else {
            break;
        }
    }

    Ok(name.to_lowercase())
}

fn parse_identifier(chars: &mut std::iter::Peekable<std::str::Chars>) -> Result<String> {
    let mut name = String::new();

    while let Some(&ch) = chars.peek() {
        if ch.is_ascii_alphanumeric() || ch == '_' || ch == '.' || ch == '$' {
            name.push(chars.next().unwrap());
        } else {
            break;
        }
    }

    Ok(name)
}

fn parse_directive(chars: &mut std::iter::Peekable<std::str::Chars>) -> Result<Token> {
    let mut name = String::new();
    name.push(chars.next().unwrap()); // consume '.'

    while let Some(&ch) = chars.peek() {
        if ch.is_ascii_alphanumeric() || ch == '_' || ch == '.' || ch == '$' {
            name.push(chars.next().unwrap());
        } else {
            break;
        }
    }

    Ok(Token::Directive(name.to_lowercase()))
}

fn parse_string_literal(chars: &mut std::iter::Peekable<std::str::Chars>) -> Result<Token> {
    chars.next(); // consume opening '"'
    let mut content = String::new();

    while let Some(&ch) = chars.peek() {
        if ch == '"' {
            chars.next(); // consume closing '"'
            return Ok(Token::String(content));
        }
        if ch == '\\' {
            chars.next();
            if let Some(&escaped) = chars.peek() {
                match escaped {
                    'n' => content.push('\n'),
                    't' => content.push('\t'),
                    'r' => content.push('\r'),
                    '\\' => content.push('\\'),
                    '"' => content.push('"'),
                    _ => {
                        content.push('\\');
                        content.push(chars.next().unwrap());
                    }
                }
                chars.next();
            }
        } else {
            content.push(chars.next().unwrap());
        }
    }

    Err(AssemblerError::LexerError(
        "unterminated string literal".to_string(),
    ))
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

    #[test]
    fn test_tokenize_local_dot_label() {
        let tokens = tokenize(".Lclear_done:").unwrap();
        assert_eq!(tokens.len(), 1);
        assert_eq!(tokens[0], Token::Label(".lclear_done".to_string()));
    }

    #[test]
    fn test_tokenize_custom_mnemonic_with_dot() {
        let tokens = tokenize("NMATVEC.F32 t1, t0").unwrap();
        assert_eq!(tokens[0], Token::Mnemonic("NMATVEC.F32".to_string()));
    }
}

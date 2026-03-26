//! RV32 Assembler Library - Phase D.1 Foundation
//!
//! Scope: RV32I + RV32F instruction encoding with directives and pseudo-instructions.
//! Outputs ELF32 object files with relocation support.

pub mod error;
pub mod instruction;
pub mod lexer;
pub mod parser;
pub mod encoder;
pub mod elf_writer;

pub use error::{AssemblerError, Result};
pub use parser::Parser;
pub use encoder::Encoder;
pub use lexer::Token;
pub use elf_writer::ElfWriter;

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

/// Assemble multiple lines of assembly code to ELF32 object file.
/// Returns ELF binary with proper relocations for linker.
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
    
    // Initialize ELF writer
    let mut elf = ElfWriter::new();
    elf.add_section(".text", 1, 0x6);  // SHT_PROGBITS, SHF_ALLOC | SHF_EXECINSTR
    elf.add_section(".data", 1, 0x3);  // SHT_PROGBITS, SHF_ALLOC | SHF_WRITE
    elf.add_section(".rodata", 1, 0x2);  // SHT_PROGBITS, SHF_ALLOC
    elf.add_section(".bss", 8, 0x3);   // SHT_NOBITS, SHF_ALLOC | SHF_WRITE

    // First pass: collect labels and identify sections
    let mut label_map = std::collections::HashMap::new();
    let mut section_offsets = std::collections::HashMap::new();
    let mut current_section = ".text".to_string();
    let mut section_byte_offset = 0;
    let mut globl_symbols: std::collections::HashSet<String> = std::collections::HashSet::new();
    
    for line in &lines {
        let tokens = match lexer::tokenize(line) {
            Ok(t) => t,
            Err(_) => continue,
        };
        
        if tokens.is_empty() {
            continue;
        }
        
        // Handle directives
        if let Some(Token::Directive(directive)) = tokens.first() {
            if directive == ".section" {
                // .section takes an argument (next token should be a directive or mnemonic)
                if !section_offsets.contains_key(&current_section) {
                    section_offsets.insert(current_section.clone(), section_byte_offset);
                }
                if tokens.len() > 1 {
                    if let Some(Token::Directive(section_name)) = tokens.get(1) {
                        // Directive tokens already have the dot
                        current_section = section_name.clone();
                    } else if let Some(Token::Mnemonic(section_name)) = tokens.get(1) {
                        // Handle case where section name is parsed as mnemonic
                        current_section = format!(".{}", section_name);
                    }
                }
                section_byte_offset = 0;
            } else if matches!(directive.as_str(), ".text" | ".data" | ".rodata" | ".bss") {
                // Bare section directives (e.g., `.data` instead of `.section .data`)
                if !section_offsets.contains_key(&current_section) {
                    section_offsets.insert(current_section.clone(), section_byte_offset);
                }
                current_section = directive.clone();
                section_byte_offset = 0;
            } else if directive == ".globl" {
                // .globl takes an argument (next token should be a mnemonic)
                if tokens.len() > 1 {
                    if let Some(Token::Mnemonic(symbol_name)) = tokens.get(1) {
                        globl_symbols.insert(symbol_name.clone());
                    }
                }
            } else if directive == ".string" {
                // Handle .string directive - grab the following string token
                if tokens.len() > 1 {
                    if let Some(Token::String(content)) = tokens.get(1) {
                        // .string is null-terminated
                        let size = content.len() + 1;
                        section_byte_offset += size;
                    }
                }
            }
            continue;
        }
        
        // Check for labels
        if let Some(Token::Label(label_name)) = tokens.first() {
            label_map.insert(label_name.clone(), (current_section.clone(), section_byte_offset));
            continue;
        }
        
        // Calculate size for actual instructions
        let size = simulate_line_size(&tokens)?;
        section_byte_offset += size;
    }
    
    if !section_offsets.contains_key(&current_section) {
        section_offsets.insert(current_section.clone(), section_byte_offset);
    }
    
    // Add symbols to ELF
    for (label_name, (section_name, offset)) in &label_map {
        let is_global = globl_symbols.contains(label_name);
        elf.add_symbol(label_name, Some(section_name), *offset, is_global, 0)?;
    }
    
    // Second pass: assemble sections and collect relocations
    let mut current_section = ".text".to_string();
    let mut relocation_records: std::collections::HashMap<String, Vec<(usize, String, u8)>> = std::collections::HashMap::new();
    
    for line in &lines {
        let tokens = match lexer::tokenize(line) {
            Ok(t) => t,
            Err(_) => continue,
        };
        
        if tokens.is_empty() {
            continue;
        }
        
        // Handle directives
        if let Some(Token::Directive(directive)) = tokens.first() {
            if directive == ".section" {
                // .section takes an argument (next token should be a directive or mnemonic)
                if tokens.len() > 1 {
                    if let Some(Token::Directive(section_name)) = tokens.get(1) {
                        // Directive tokens already have the dot
                        current_section = section_name.clone();
                    } else if let Some(Token::Mnemonic(section_name)) = tokens.get(1) {
                        // Handle case where section name is parsed as mnemonic
                        current_section = format!(".{}", section_name);
                    }
                }
            } else if matches!(directive.as_str(), ".text" | ".data" | ".rodata" | ".bss") {
                // Bare section directives (e.g., `.data` instead of `.section .data`)
                current_section = directive.clone();
            } else if directive == ".string" {
                // Handle .string directive - grab the following string token
                if tokens.len() > 1 {
                    if let Some(Token::String(content)) = tokens.get(1) {
                        let mut string_bytes = content.as_bytes().to_vec();
                        string_bytes.push(0); // null terminator
                        elf.append_to_section(&current_section, &string_bytes)?;
                    }
                }
            }
            continue;
        }
        
        // Skip labels
        match tokens.first() {
            Some(Token::Label(_)) => continue,
            _ => {}
        }
        
        // Assemble line
        let (words, relocs) = assemble_line_with_relocations(line, &label_map, elf.get_section_size(&current_section))?;
        
        // Add words to section
        for word in words {
            elf.append_to_section(&current_section, &word)?;
        }
        
        // Collect relocations
        for (offset, symbol_name, reloc_type) in relocs {
            relocation_records.entry(current_section.clone()).or_insert_with(Vec::new).push((offset, symbol_name, reloc_type));
        }
    }
    
    // Add relocations to ELF
    for (section_name, relocs) in relocation_records {
        for (offset, symbol_name, reloc_type) in relocs {
            if let Some(symbol_idx) = elf.get_symbol_index(&symbol_name) {
                elf.add_relocation(&section_name, offset, symbol_idx, reloc_type)?;
            }
        }
    }
    
    // Write ELF file
    elf.write()
}

/// Simulate assembly of a line to determine its size without actually encoding
fn simulate_line_size(tokens: &[Token]) -> Result<usize> {
    if tokens.is_empty() {
        return Ok(0);
    }
    
    if let Some(Token::Mnemonic(mnemonic)) = tokens.first() {
        if mnemonic == "li" && tokens.len() == 4 {
            // Check if imm fits in 12 bits
            if let Token::Integer(imm) = &tokens[3] {
                if *imm >= -2048 && *imm <= 2047 {
                    return Ok(4);  // Single addi
                } else {
                    return Ok(8);  // lui + addi
                }
            }
            return Ok(8);  // Conservative
        } else if mnemonic == "la" && tokens.len() == 4 {
            // la always expands to 8 bytes (auipc + addi)
            return Ok(8);
        } else if ["beq", "bne", "blt", "bltu", "bge", "bgeu", "jal"].contains(&mnemonic.as_str()) {
            return Ok(4);  // Branch/jump with label resolution
        } else {
            return Ok(4);  // Regular instruction
        }
    }
    
    Ok(0)
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
                    if let Some(_label_offset) = label_map.get(symbol) {
                        // For object file compatibility, emit 0 as a placeholder when the symbol is in a different section
                        // The linker will fix up the actual offset using relocations
                        // This matches GNU assembler behavior for object files (pre-linking)
                        let offset = 0;
                        return expand_la_with_offset(rd, offset);
                    }
                    // If label not found, skip the instruction (return None like the parser does)
                    // This matches the original behavior where la was treated as a pseudo-instruction
                    return Ok(Vec::new());
                }
            }
        } else if mnemonic == "j" && tokens.len() == 2 {
            // j label - pseudo for jal x0, label
            if let Token::Mnemonic(label_name) = &tokens[1] {
                if let Some(&label_offset) = label_map.get(label_name) {
                    let imm = label_offset as i64 - current_byte_offset as i64;
                    let instr = instruction::Instruction::JType {
                        mnemonic: "jal".to_string(),
                        rd: instruction::Register::X0,
                        imm,
                    };
                    let encoded = Encoder::encode(&instr)?;
                    return Ok(vec![encoded]);
                }
            }
        } else if mnemonic == "mv" && tokens.len() == 4 {
            // mv rd, rs - pseudo for addi rd, rs, 0
            if let (Token::Mnemonic(rd_name), Token::Comma, Token::Mnemonic(rs_name)) =
                (&tokens[1], &tokens[2], &tokens[3])
            {
                use instruction::Register;
                if let (Some(rd), Some(rs)) = (Register::from_name(rd_name), Register::from_name(rs_name)) {
                    let instr = instruction::Instruction::IType {
                        mnemonic: "addi".to_string(),
                        rd,
                        rs1: rs,
                        imm: 0,
                    };
                    let encoded = Encoder::encode(&instr)?;
                    return Ok(vec![encoded]);
                }
            }
        } else if mnemonic == "ret" && tokens.len() == 1 {
            // ret - pseudo for jalr x0, x1, 0
            let instr = instruction::Instruction::IType {
                mnemonic: "jalr".to_string(),
                rd: instruction::Register::X0,
                rs1: instruction::Register::X1,
                imm: 0,
            };
            let encoded = Encoder::encode(&instr)?;
            return Ok(vec![encoded]);
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

/// Assemble a line with relocation tracking
/// Returns (instructions, relocations) where relocations are (offset, symbol_name, reloc_type)
fn assemble_line_with_relocations(
    line: &str,
    label_map: &std::collections::HashMap<String, (String, usize)>,
    current_byte_offset: usize,
) -> Result<(Vec<[u8; 4]>, Vec<(usize, String, u8)>)> {
    let tokens = lexer::tokenize(line)?;
    let mut relocations = Vec::new();
    
    if tokens.is_empty() {
        return Ok((Vec::new(), relocations));
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
                    let instructions = expand_li(rd, *imm)?;
                    return Ok((instructions, relocations));
                }
            }
        } else if mnemonic == "la" && tokens.len() == 4 {
            // la rd, symbol - expands to auipc + addi with relocations
            if let (Token::Mnemonic(rd_name), Token::Comma, Token::Mnemonic(symbol)) =
                (&tokens[1], &tokens[2], &tokens[3])
            {
                use instruction::Register;
                if let Some(rd) = Register::from_name(rd_name) {
                    // Emit with placeholder offsets (0)
                    let instructions = expand_la_with_offset(rd, 0)?;
                    
                    // Record relocations for the linker
                    // Relocation at offset current_byte_offset for auipc (HI20)
                    relocations.push((current_byte_offset, symbol.clone(), elf_writer::R_RISCV_PCREL_HI20));
                    relocations.push((current_byte_offset, "".to_string(), elf_writer::R_RISCV_RELAX));
                    
                    // Relocation at offset current_byte_offset + 4 for addi (LO12I)
                    relocations.push((current_byte_offset + 4, symbol.clone(), elf_writer::R_RISCV_PCREL_LO12_I));
                    relocations.push((current_byte_offset + 4, "".to_string(), elf_writer::R_RISCV_RELAX));
                    
                    return Ok((instructions, relocations));
                }
            }
        } else if mnemonic == "j" && tokens.len() == 2 {
            // j label - pseudo for jal x0, label
            if let Token::Mnemonic(label_name) = &tokens[1] {
                if let Some((_, label_offset)) = label_map.get(label_name) {
                    let imm = *label_offset as i64 - current_byte_offset as i64;
                    let instr = instruction::Instruction::JType {
                        mnemonic: "jal".to_string(),
                        rd: instruction::Register::X0,
                        imm,
                    };
                    let encoded = Encoder::encode(&instr)?;
                    return Ok((vec![encoded], relocations));
                }
            }
        } else if mnemonic == "mv" && tokens.len() == 4 {
            // mv rd, rs - pseudo for addi rd, rs, 0
            if let (Token::Mnemonic(rd_name), Token::Comma, Token::Mnemonic(rs_name)) =
                (&tokens[1], &tokens[2], &tokens[3])
            {
                use instruction::Register;
                if let (Some(rd), Some(rs)) = (Register::from_name(rd_name), Register::from_name(rs_name)) {
                    let instr = instruction::Instruction::IType {
                        mnemonic: "addi".to_string(),
                        rd,
                        rs1: rs,
                        imm: 0,
                    };
                    let encoded = Encoder::encode(&instr)?;
                    return Ok((vec![encoded], relocations));
                }
            }
        } else if mnemonic == "ret" && tokens.len() == 1 {
            // ret - pseudo for jalr x0, x1, 0
            let instr = instruction::Instruction::IType {
                mnemonic: "jalr".to_string(),
                rd: instruction::Register::X0,
                rs1: instruction::Register::X1,
                imm: 0,
            };
            let encoded = Encoder::encode(&instr)?;
            return Ok((vec![encoded], relocations));
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
                        if let Some((_, label_offset)) = label_map.get(label_name) {
                            let imm = *label_offset as i64 - current_byte_offset as i64;
                            let instruction = instruction::Instruction::BType {
                                mnemonic: mnemonic.clone(),
                                rs1,
                                rs2,
                                imm,
                            };
                            let encoded = Encoder::encode(&instruction)?;
                            return Ok((vec![encoded], relocations));
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
                        if let Some((_, label_offset)) = label_map.get(label_name) {
                            let imm = *label_offset as i64 - current_byte_offset as i64;
                            let instruction = instruction::Instruction::JType {
                                mnemonic: mnemonic.clone(),
                                rd,
                                imm,
                            };
                            let encoded = Encoder::encode(&instruction)?;
                            return Ok((vec![encoded], relocations));
                        }
                    }
                }
            }
        }
    }

    // Regular instruction
    if let Some(instruction) = Parser::parse_instruction(&tokens)? {
        let encoded = Encoder::encode(&instruction)?;
        Ok((vec![encoded], relocations))
    } else {
        Ok((Vec::new(), relocations))
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


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

fn token_to_register(token: &Token) -> Option<instruction::Register> {
    match token {
        Token::Register(name) | Token::Mnemonic(name) => instruction::Register::from_name(name),
        _ => None,
    }
}

fn token_to_section_name(token: &Token) -> Option<String> {
    match token {
        Token::Directive(name) => Some(name.clone()),
        Token::Mnemonic(name) => Some(format!(".{}", name)),
        _ => None,
    }
}

fn parse_integer_list(tokens: &[Token]) -> Result<Vec<i64>> {
    if tokens.is_empty() {
        return Ok(Vec::new());
    }

    let mut values = Vec::new();
    let mut expect_value = true;

    for token in tokens {
        if expect_value {
            if let Token::Integer(v) = token {
                values.push(*v);
                expect_value = false;
            } else {
                return Err(AssemblerError::InvalidOperand(format!(
                    "expected integer, got {}",
                    token
                )));
            }
        } else if !matches!(token, Token::Comma) {
            return Err(AssemblerError::InvalidOperand(format!(
                "expected comma, got {}",
                token
            )));
        } else {
            expect_value = true;
        }
    }

    if expect_value {
        return Err(AssemblerError::ParserError(
            "trailing comma in data directive".to_string(),
        ));
    }

    Ok(values)
}

fn alignment_padding(current: usize, align: usize) -> usize {
    if align <= 1 {
        0
    } else {
        (align - (current % align)) % align
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
                if let Some(section_name) = tokens.get(1).and_then(token_to_section_name) {
                    current_section = section_name;
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
            } else if directive == ".ascii" || directive == ".asciz" {
                if let Some(Token::String(content)) = tokens.get(1) {
                    section_byte_offset += content.len();
                    if directive == ".asciz" {
                        section_byte_offset += 1;
                    }
                }
            } else if directive == ".byte" {
                let values = parse_integer_list(&tokens[1..])?;
                section_byte_offset += values.len();
            } else if directive == ".half" {
                let values = parse_integer_list(&tokens[1..])?;
                section_byte_offset += values.len() * 2;
            } else if directive == ".word" {
                let values = parse_integer_list(&tokens[1..])?;
                section_byte_offset += values.len() * 4;
            } else if directive == ".align" {
                if let Some(Token::Integer(pow2)) = tokens.get(1) {
                    let align = if *pow2 <= 0 {
                        1usize
                    } else {
                        1usize << (*pow2 as usize)
                    };
                    section_byte_offset += alignment_padding(section_byte_offset, align);
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
                if let Some(section_name) = tokens.get(1).and_then(token_to_section_name) {
                    current_section = section_name;
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
            } else if directive == ".ascii" || directive == ".asciz" {
                if let Some(Token::String(content)) = tokens.get(1) {
                    let mut bytes = content.as_bytes().to_vec();
                    if directive == ".asciz" {
                        bytes.push(0);
                    }
                    elf.append_to_section(&current_section, &bytes)?;
                }
            } else if directive == ".byte" {
                let values = parse_integer_list(&tokens[1..])?;
                let mut out = Vec::with_capacity(values.len());
                for v in values {
                    out.push((v as i8) as u8);
                }
                elf.append_to_section(&current_section, &out)?;
            } else if directive == ".half" {
                let values = parse_integer_list(&tokens[1..])?;
                let mut out = Vec::with_capacity(values.len() * 2);
                for v in values {
                    out.extend_from_slice(&(v as i16).to_le_bytes());
                }
                elf.append_to_section(&current_section, &out)?;
            } else if directive == ".word" {
                let values = parse_integer_list(&tokens[1..])?;
                let mut out = Vec::with_capacity(values.len() * 4);
                for v in values {
                    out.extend_from_slice(&(v as i32).to_le_bytes());
                }
                elf.append_to_section(&current_section, &out)?;
            } else if directive == ".align" {
                if let Some(Token::Integer(pow2)) = tokens.get(1) {
                    let align = if *pow2 <= 0 {
                        1usize
                    } else {
                        1usize << (*pow2 as usize)
                    };
                    let current_size = elf.get_section_size(&current_section);
                    let pad = alignment_padding(current_size, align);
                    if pad > 0 {
                        let zeros = vec![0u8; pad];
                        elf.append_to_section(&current_section, &zeros)?;
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
                let imm32 = *imm as i32 as i64;
                if imm32 >= -2048 && imm32 <= 2047 {
                    return Ok(4);  // Single addi
                } else {
                    let upper_signed = (imm32 + 0x800) >> 12;
                    let lower_signed = imm32 - (upper_signed << 12);
                    if lower_signed == 0 {
                        return Ok(4); // Single lui
                    }
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
    } else if let Some(Token::Directive(directive)) = tokens.first() {
        match directive.as_str() {
            ".string" => {
                if let Some(Token::String(s)) = tokens.get(1) {
                    return Ok(s.len() + 1);
                }
            }
            ".ascii" => {
                if let Some(Token::String(s)) = tokens.get(1) {
                    return Ok(s.len());
                }
            }
            ".asciz" => {
                if let Some(Token::String(s)) = tokens.get(1) {
                    return Ok(s.len() + 1);
                }
            }
            ".byte" => {
                return Ok(parse_integer_list(&tokens[1..])?.len());
            }
            ".half" => {
                return Ok(parse_integer_list(&tokens[1..])?.len() * 2);
            }
            ".word" => {
                return Ok(parse_integer_list(&tokens[1..])?.len() * 4);
            }
            _ => {}
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
    
    // GNU-compatible RV32 behavior: treat literals as 32-bit values.
    let imm32 = imm as i32 as i64;

    if imm32 >= -2048 && imm32 <= 2047 {
        // Fits in 12 bits, single addi
        let instr = Instruction::IType {
            mnemonic: "addi".to_string(),
            rd,
            rs1: instruction::Register::X0,
            imm: imm32,
        };
        result.push(Encoder::encode(&instr)?);
    } else {
        // Need lui + addi
        // Split into HI20/LO12 with proper rounding so LO12 is signed 12-bit.
        let upper_signed = (imm32 + 0x800) >> 12;
        let upper_field = upper_signed & 0xFFFFF;
        let lower_signed = imm32 - (upper_signed << 12);
        
        // Emit lui
        let lui_instr = Instruction::UType {
            mnemonic: "lui".to_string(),
            rd,
            imm: upper_field,
        };
        result.push(Encoder::encode(&lui_instr)?);
        
        // Emit addi only when needed.
        if lower_signed != 0 {
            let addi_instr = Instruction::IType {
                mnemonic: "addi".to_string(),
                rd,
                rs1: rd,
                imm: lower_signed,
            };
            result.push(Encoder::encode(&addi_instr)?);
        }
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
            if let (Token::Comma, Token::Integer(imm)) =
                (&tokens[2], &tokens[3])
            {
                if let Some(rd) = token_to_register(&tokens[1]) {
                    return expand_li(rd, *imm);
                }
            }
        } else if mnemonic == "la" && tokens.len() == 4 {
            // la rd, symbol - expands to auipc + addi with label resolution
            if let (Token::Comma, Token::Mnemonic(symbol)) =
                (&tokens[2], &tokens[3])
            {
                if let Some(rd) = token_to_register(&tokens[1]) {
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
            if let Token::Comma = &tokens[2] {
                if let (Some(rd), Some(rs)) = (token_to_register(&tokens[1]), token_to_register(&tokens[3])) {
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
                if let (Token::Comma, Token::Comma, Token::Mnemonic(label_name)) =
                    (&tokens[2], &tokens[4], &tokens[5])
                {
                    if let (Some(rs1), Some(rs2)) = (token_to_register(&tokens[1]), token_to_register(&tokens[3])) {
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
                if let (Token::Comma, Token::Mnemonic(label_name)) =
                    (&tokens[2], &tokens[3])
                {
                    if let Some(rd) = token_to_register(&tokens[1]) {
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
            if let (Token::Comma, Token::Integer(imm)) = (&tokens[2], &tokens[3]) {
                if let Some(rd) = token_to_register(&tokens[1]) {
                    let instructions = expand_li(rd, *imm)?;
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
            if let Token::Comma = &tokens[2] {
                if let (Some(rd), Some(rs)) = (token_to_register(&tokens[1]), token_to_register(&tokens[3])) {
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
        } else if mnemonic == "la" && tokens.len() == 4 {
            // la rd, symbol - expands to auipc + addi with relocations
            if let (Token::Comma, Token::Mnemonic(symbol)) = (&tokens[2], &tokens[3]) {
                if let Some(rd) = token_to_register(&tokens[1]) {
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
            if let Token::Comma = &tokens[2] {
                if let (Some(rd), Some(rs)) = (token_to_register(&tokens[1]), token_to_register(&tokens[3])) {
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
                if let (Token::Comma, Token::Comma, Token::Mnemonic(label_name)) =
                    (&tokens[2], &tokens[4], &tokens[5])
                {
                    if let (Some(rs1), Some(rs2)) = (token_to_register(&tokens[1]), token_to_register(&tokens[3])) {
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
                if let (Token::Comma, Token::Mnemonic(label_name)) =
                    (&tokens[2], &tokens[3])
                {
                    if let Some(rd) = token_to_register(&tokens[1]) {
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

        let bytes = result.unwrap().expect("expected an instruction");
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
        // ELF output, not raw .text bytes
        assert!(!result.unwrap().is_empty());
    }

    #[test]
    fn test_data_directives_and_li_large_imm() {
        let program = r#"
            .section .text
            .globl _start
        _start:
            li t0, 0xDEADBEEF
            li t1, 65535
            jalr ra, 0(t0)

            .section .data
            bytes: .byte 0x41, 0x42
            halfv: .half 0x1234
            wordv: .word 0x12345678
            msg1: .ascii "A"
            msg2: .asciz "B"
            .align 2
            msg3: .string "C"
        "#;

        let bytes = assemble_program(program).expect("assemble_program failed");
        assert!(!bytes.is_empty());
    }
}

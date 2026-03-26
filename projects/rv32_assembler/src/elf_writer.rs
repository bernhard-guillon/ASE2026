/// ELF32 writer for RISC-V object files
/// Produces relocatable ELF32 files compatible with GNU linker
///
/// Two-pass approach:
/// 1. Calculate sizes of all sections, tables, headers
/// 2. Write with correct file offsets

use std::collections::BTreeMap;
use crate::error::{AssemblerError, Result};

// ELF constants
const ELF_MAGIC: [u8; 4] = [0x7F, b'E', b'L', b'F'];
const ELF_CLASS_32: u8 = 1;
const ELF_DATA_LITTLE_ENDIAN: u8 = 1;
const ELF_VERSION: u8 = 1;
const ELF_OSABI_SYSV: u8 = 0;

const EM_RISCV: u16 = 243;
const ET_REL: u16 = 1;  // Relocatable object

// Section types
const SHT_NULL: u32 = 0;
const SHT_PROGBITS: u32 = 1;
const SHT_SYMTAB: u32 = 2;
const SHT_STRTAB: u32 = 3;
const SHT_REL: u32 = 9;
const SHT_NOBITS: u32 = 8;

// Section flags
const SHF_WRITE: u32 = 0x1;
const SHF_ALLOC: u32 = 0x2;
const SHF_EXECINSTR: u32 = 0x4;

// Symbol binding
const STB_LOCAL: u8 = 0;
const STB_GLOBAL: u8 = 1;

// Symbol type
const STT_NOTYPE: u8 = 0;

// Symbol visibility
const STV_DEFAULT: u8 = 0;

// RISC-V relocation types - exported for use in assembler
pub const R_RISCV_JAL: u8 = 17;
pub const R_RISCV_CALL_PLT: u8 = 19;
pub const R_RISCV_PCREL_HI20: u8 = 23;
pub const R_RISCV_PCREL_LO12_I: u8 = 24;
pub const R_RISCV_RELAX: u8 = 51;

#[derive(Clone, Debug)]
pub struct Symbol {
    pub name: String,
    pub section_idx: Option<usize>,  // None for undefined symbols
    pub offset: usize,               // Offset within section
    pub is_global: bool,
    pub st_type: u8,
}

#[derive(Clone, Debug)]
pub struct Relocation {
    pub offset: usize,
    pub symbol_idx: usize,
    pub reloc_type: u8,
}

struct SectionData {
    section_type: u32,
    flags: u32,
    data: Vec<u8>,
}

struct StringTable {
    strings: Vec<String>,
    offset_map: BTreeMap<String, usize>,
}

impl StringTable {
    fn new() -> Self {
        let mut st = StringTable {
            strings: vec!["".to_string()],
            offset_map: BTreeMap::new(),
        };
        st.offset_map.insert("".to_string(), 0);
        st
    }

    fn add(&mut self, s: &str) -> usize {
        if let Some(&offset) = self.offset_map.get(s) {
            return offset;
        }
        let offset = self.strings.iter().map(|x| x.len() + 1).sum();
        self.strings.push(s.to_string());
        self.offset_map.insert(s.to_string(), offset);
        offset
    }

    fn to_bytes(&self) -> Vec<u8> {
        let mut bytes = Vec::new();
        for s in &self.strings {
            bytes.extend_from_slice(s.as_bytes());
            bytes.push(0);
        }
        bytes
    }
}

pub struct ElfWriter {
    sections: BTreeMap<String, SectionData>,
    symbols: Vec<Symbol>,
    string_table: StringTable,
    section_string_table: StringTable,
    relocations: BTreeMap<String, Vec<Relocation>>,
}

impl ElfWriter {
    pub fn new() -> Self {
        let mut writer = ElfWriter {
            sections: BTreeMap::new(),
            symbols: vec![Symbol {
                name: "".to_string(),
                section_idx: None,
                offset: 0,
                is_global: false,
                st_type: STT_NOTYPE,
            }],
            string_table: StringTable::new(),
            section_string_table: StringTable::new(),
            relocations: BTreeMap::new(),
        };

        // Add standard section names
        writer.section_string_table.add("");
        writer.section_string_table.add(".text");
        writer.section_string_table.add(".data");
        writer.section_string_table.add(".rodata");
        writer.section_string_table.add(".bss");
        writer.section_string_table.add(".symtab");
        writer.section_string_table.add(".strtab");
        writer.section_string_table.add(".shstrtab");
        writer.section_string_table.add(".rel.text");
        writer.section_string_table.add(".rel.data");

        writer
    }

    pub fn add_section(&mut self, name: &str, section_type: u32, flags: u32) {
        self.sections.insert(
            name.to_string(),
            SectionData {
                section_type,
                flags,
                data: Vec::new(),
            },
        );
    }

    pub fn append_to_section(&mut self, name: &str, data: &[u8]) -> Result<()> {
        self.sections
            .get_mut(name)
            .ok_or_else(|| AssemblerError::EncoderError(format!("Section {} not found", name)))?
            .data
            .extend_from_slice(data);
        Ok(())
    }

    pub fn get_section_size(&self, name: &str) -> usize {
        self.sections
            .get(name)
            .map(|s| s.data.len())
            .unwrap_or(0)
    }

    pub fn add_symbol(&mut self, name: &str, section_name: Option<&str>, offset: usize, is_global: bool, st_type: u8) -> Result<usize> {
        let section_idx = if let Some(sect_name) = section_name {
            Some(
                self.sections
                    .keys()
                    .position(|x| x == sect_name)
                    .ok_or_else(|| AssemblerError::EncoderError(format!("Section {} not found", sect_name)))?,
            )
        } else {
            None
        };

        let symbol = Symbol {
            name: name.to_string(),
            section_idx,
            offset,
            is_global,
            st_type,
        };

        self.symbols.push(symbol);
        self.string_table.add(name);
        Ok(self.symbols.len() - 1)
    }

    pub fn add_relocation(&mut self, section_name: &str, offset: usize, symbol_idx: usize, reloc_type: u8) -> Result<()> {
        self.relocations
            .entry(section_name.to_string())
            .or_insert_with(Vec::new)
            .push(Relocation {
                offset,
                symbol_idx,
                reloc_type,
            });
        Ok(())
    }

    pub fn get_symbol_index(&self, name: &str) -> Option<usize> {
        self.symbols.iter().position(|sym| sym.name == name)
    }

    pub fn write(&self) -> Result<Vec<u8>> {
        let mut output = Vec::new();

        // PASS 1: Calculate sizes and offsets
        const ELF_HEADER_SIZE: usize = 52;
        let mut file_offset = ELF_HEADER_SIZE;

        // Collect emitted allocatable sections in deterministic order.
        let mut emitted_sections: Vec<(&String, &SectionData)> = Vec::new();
        let mut emitted_section_indices: BTreeMap<String, usize> = BTreeMap::new();
        let mut original_to_emitted: BTreeMap<usize, usize> = BTreeMap::new();
        for (orig_idx, (name, section)) in self.sections.iter().enumerate() {
            if section.data.len() > 0 || name == ".bss" {
                let emitted_idx = 1 + emitted_sections.len();
                emitted_sections.push((name, section));
                emitted_section_indices.insert(name.clone(), emitted_idx);
                original_to_emitted.insert(orig_idx, emitted_idx);
            }
        }

        // Calculate section offsets (NOBITS sections do not consume file bytes).
        let mut section_offsets: BTreeMap<String, (usize, usize)> = BTreeMap::new(); // name -> (offset, size)
        for (name, section) in &emitted_sections {
            let size = section.data.len();
            section_offsets.insert((*name).clone(), (file_offset, size));
            if section.section_type != SHT_NOBITS && size > 0 {
                file_offset += size;
            }
        }

        // Symbol table size
        let symtab_size = self.symbols.len() * 16;
        let symtab_offset = file_offset;
        file_offset += symtab_size;

        // String table size
        let strtab_data = self.string_table.to_bytes();
        let strtab_offset = file_offset;
        file_offset += strtab_data.len();

        // Section header string table size
        let shstrtab_data = self.section_string_table.to_bytes();
        let shstrtab_offset = file_offset;
        file_offset += shstrtab_data.len();

        // Relocation table offsets and ordered entries.
        let mut reloc_entries: Vec<(String, String, usize, usize)> = Vec::new();
        for (section_name, relocs) in &self.relocations {
            if !relocs.is_empty() && emitted_section_indices.contains_key(section_name) {
                let rel_section_name = format!(".rel{}", section_name);
                let reloc_size = relocs.len() * 8;
                reloc_entries.push((
                    rel_section_name,
                    section_name.clone(),
                    file_offset,
                    reloc_size,
                ));
                file_offset += reloc_size;
            }
        }

        let symtab_index = 1 + emitted_sections.len();
        let strtab_index = symtab_index + 1;
        let shstrtab_index = strtab_index + 1;

        // Section header table offset
        let e_shoff = file_offset;
        let num_sections = 1 + emitted_sections.len() + 3 + reloc_entries.len(); // null + allocatable sections + symtab/strtab/shstrtab + reloc sections

        // PASS 2: Write file
        
        // Write ELF header
        output.extend_from_slice(&ELF_MAGIC);
        output.push(ELF_CLASS_32);
        output.push(ELF_DATA_LITTLE_ENDIAN);
        output.push(ELF_VERSION);
        output.push(ELF_OSABI_SYSV);
        output.push(0);  // ABI version
        output.extend_from_slice(&[0; 7]);  // padding

        output.extend_from_slice(&u16::to_le_bytes(ET_REL));
        output.extend_from_slice(&u16::to_le_bytes(EM_RISCV));
        output.extend_from_slice(&u32::to_le_bytes(1));  // e_version
        output.extend_from_slice(&u32::to_le_bytes(0));  // e_entry
        output.extend_from_slice(&u32::to_le_bytes(0));  // e_phoff
        output.extend_from_slice(&u32::to_le_bytes(e_shoff as u32));
        output.extend_from_slice(&u32::to_le_bytes(0));  // e_flags
        output.extend_from_slice(&u16::to_le_bytes(ELF_HEADER_SIZE as u16));  // e_ehsize
        output.extend_from_slice(&u16::to_le_bytes(0));  // e_phentsize
        output.extend_from_slice(&u16::to_le_bytes(0));  // e_phnum
        output.extend_from_slice(&u16::to_le_bytes(40));  // e_shentsize
        output.extend_from_slice(&u16::to_le_bytes(num_sections as u16));  // e_shnum
        output.extend_from_slice(&u16::to_le_bytes(shstrtab_index as u16));  // e_shstrndx

        // Write allocatable section payloads in the same order used for offsets.
        for (_name, section) in &emitted_sections {
            if section.section_type != SHT_NOBITS && !section.data.is_empty() {
                output.extend_from_slice(&section.data);
            }
        }

        // Write symbol table with local symbols first (required by ELF).
        let mut local_symbols: Vec<usize> = Vec::new();
        let mut global_symbols: Vec<usize> = Vec::new();
        for old_idx in 1..self.symbols.len() {
            if self.symbols[old_idx].is_global {
                global_symbols.push(old_idx);
            } else {
                local_symbols.push(old_idx);
            }
        }
        let mut symbol_order: Vec<usize> = Vec::with_capacity(self.symbols.len());
        symbol_order.push(0); // null symbol
        symbol_order.extend(local_symbols.iter().copied());
        symbol_order.extend(global_symbols.iter().copied());

        let mut old_to_new_symbol: Vec<usize> = vec![0; self.symbols.len()];
        for (new_idx, old_idx) in symbol_order.iter().enumerate() {
            old_to_new_symbol[*old_idx] = new_idx;
        }

        for old_idx in &symbol_order {
            let symbol = &self.symbols[*old_idx];
            let st_name = self.string_table.offset_map.get(&symbol.name).copied().unwrap_or(0);
            let st_value = symbol.offset as u32;
            let st_size = 0;
            let st_info = ((if symbol.is_global { STB_GLOBAL } else { STB_LOCAL }) << 4) | symbol.st_type;
            let st_other = STV_DEFAULT;
            let st_shndx = if let Some(sect_idx) = symbol.section_idx {
                original_to_emitted.get(&sect_idx).copied().unwrap_or(0) as u16
            } else {
                0
            };

            output.extend_from_slice(&u32::to_le_bytes(st_name as u32));
            output.extend_from_slice(&u32::to_le_bytes(st_value));
            output.extend_from_slice(&u32::to_le_bytes(st_size as u32));
            output.push(st_info);
            output.push(st_other);
            output.extend_from_slice(&u16::to_le_bytes(st_shndx));
        }

        // Write string table
        output.extend_from_slice(&strtab_data);

        // Write section header string table
        output.extend_from_slice(&shstrtab_data);

        // Write relocations
        for (_rel_name, target_section, _offset, _size) in &reloc_entries {
            if let Some(relocs) = self.relocations.get(target_section) {
                for reloc in relocs {
                    let sym_idx = old_to_new_symbol
                        .get(reloc.symbol_idx)
                        .copied()
                        .ok_or_else(|| AssemblerError::EncoderError("relocation symbol index out of bounds".to_string()))?;
                let r_offset = reloc.offset as u32;
                    let r_info = ((sym_idx as u32) << 8) | (reloc.reloc_type as u32);
                output.extend_from_slice(&u32::to_le_bytes(r_offset));
                output.extend_from_slice(&u32::to_le_bytes(r_info));
            }
            }
        }

        // Write section headers
        // Section 0: null
        for _ in 0..40 {
            output.push(0);
        }

        // Section headers for allocatable sections (1+)
        for (name, section) in &emitted_sections {
            let (offset, size) = section_offsets
                .get(*name)
                .copied()
                .ok_or_else(|| AssemblerError::EncoderError(format!("missing offset for section {}", name)))?;
            self.write_section_header(
                &mut output,
                name,
                section.section_type,
                section.flags,
                offset,
                size,
                0,
                0,
                4,
                0,
            )?;
        }

        // .symtab
        {
            let sh_name = self.section_string_table.offset_map.get(".symtab").copied().unwrap_or(0);
            output.extend_from_slice(&u32::to_le_bytes(sh_name as u32));
            output.extend_from_slice(&u32::to_le_bytes(SHT_SYMTAB));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(symtab_offset as u32));
            output.extend_from_slice(&u32::to_le_bytes(symtab_size as u32));
            output.extend_from_slice(&u32::to_le_bytes(strtab_index as u32));  // link to .strtab
            output.extend_from_slice(&u32::to_le_bytes((1 + local_symbols.len()) as u32)); // first global symbol index
            output.extend_from_slice(&u32::to_le_bytes(4));
            output.extend_from_slice(&u32::to_le_bytes(16));  // entry size
        }

        // .strtab
        {
            let sh_name = self.section_string_table.offset_map.get(".strtab").copied().unwrap_or(0);
            output.extend_from_slice(&u32::to_le_bytes(sh_name as u32));
            output.extend_from_slice(&u32::to_le_bytes(SHT_STRTAB));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(strtab_offset as u32));
            output.extend_from_slice(&u32::to_le_bytes(strtab_data.len() as u32));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(0));
        }

        // .shstrtab
        {
            let sh_name = self.section_string_table.offset_map.get(".shstrtab").copied().unwrap_or(0);
            output.extend_from_slice(&u32::to_le_bytes(sh_name as u32));
            output.extend_from_slice(&u32::to_le_bytes(SHT_STRTAB));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(shstrtab_offset as u32));
            output.extend_from_slice(&u32::to_le_bytes(shstrtab_data.len() as u32));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(0));
        }

        // Relocation sections
        for (rel_section_name, target_section, offset, size) in &reloc_entries {
            let sh_name = self.section_string_table.offset_map.get(rel_section_name).copied().unwrap_or(0);
            let sh_info = emitted_section_indices.get(target_section).copied().unwrap_or(0);

            output.extend_from_slice(&u32::to_le_bytes(sh_name as u32));
            output.extend_from_slice(&u32::to_le_bytes(SHT_REL));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(0));
            output.extend_from_slice(&u32::to_le_bytes(*offset as u32));
            output.extend_from_slice(&u32::to_le_bytes(*size as u32));
            output.extend_from_slice(&u32::to_le_bytes(symtab_index as u32));  // link to .symtab
            output.extend_from_slice(&u32::to_le_bytes(sh_info as u32));       // target section index
            output.extend_from_slice(&u32::to_le_bytes(4));
            output.extend_from_slice(&u32::to_le_bytes(8));  // entry size
        }

        Ok(output)
    }

    fn write_section_header(
        &self,
        headers: &mut Vec<u8>,
        name: &str,
        sh_type: u32,
        sh_flags: u32,
        sh_offset: usize,
        sh_size: usize,
        sh_link: u32,
        sh_info: u32,
        sh_addralign: u32,
        sh_entsize: u32,
    ) -> Result<()> {
        let sh_name = self.section_string_table.offset_map.get(name).copied().unwrap_or(0);
        headers.extend_from_slice(&u32::to_le_bytes(sh_name as u32));
        headers.extend_from_slice(&u32::to_le_bytes(sh_type));
        headers.extend_from_slice(&u32::to_le_bytes(sh_flags));
        headers.extend_from_slice(&u32::to_le_bytes(0));  // sh_addr
        headers.extend_from_slice(&u32::to_le_bytes(sh_offset as u32));
        headers.extend_from_slice(&u32::to_le_bytes(sh_size as u32));
        headers.extend_from_slice(&u32::to_le_bytes(sh_link));
        headers.extend_from_slice(&u32::to_le_bytes(sh_info));
        headers.extend_from_slice(&u32::to_le_bytes(sh_addralign));
        headers.extend_from_slice(&u32::to_le_bytes(sh_entsize));
        Ok(())
    }
}

use std::fs;
use std::path::Path;
use std::process;

use rv32_assembler::assemble_program_with_base;

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: {} <input.s> [-march <arch>] [-mabi <abi>] [-o <output.o>]", args[0]);
        process::exit(1);
    }

    let input_file = &args[1];
    let mut output_file = input_file.replace(".s", ".o");
    let mut idx = 2;

    // Parse optional flags (-march, -mabi, -o)
    while idx < args.len() {
        match args[idx].as_str() {
            "-march" => {
                idx += 2; // Skip -march and its argument (we ignore it)
            }
            "-mabi" => {
                idx += 2; // Skip -mabi and its argument (we ignore it)
            }
            "-o" => {
                if idx + 1 < args.len() {
                    output_file = args[idx + 1].clone();
                    idx += 2;
                } else {
                    eprintln!("Error: -o requires an argument");
                    process::exit(1);
                }
            }
            _ => {
                eprintln!("Unknown option: {}", args[idx]);
                process::exit(1);
            }
        }
    }

    // Read input file
    let source = match fs::read_to_string(input_file) {
        Ok(content) => content,
        Err(e) => {
            eprintln!("Error reading {}: {}", input_file, e);
            process::exit(1);
        }
    };

    // Assemble
    let input_dir = Path::new(input_file).parent();
    match assemble_program_with_base(&source, input_dir) {
        Ok(bytes) => {
            // Write output file
            if let Err(e) = fs::write(&output_file, &bytes) {
                eprintln!("Error writing {}: {}", output_file, e);
                process::exit(1);
            }

            println!("Assembled {} bytes to {}", bytes.len(), output_file);
        }
        Err(e) => {
            eprintln!("Assembly error: {}", e);
            process::exit(1);
        }
    }
}

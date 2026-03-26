use std::fs;
use std::process;

use rv32_assembler::assemble_program;

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: {} <input.s> [-o <output.o>]", args[0]);
        process::exit(1);
    }

    let input_file = &args[1];

    // Parse optional -o output file
    let output_file = if args.len() >= 4 && args[2] == "-o" {
        args[3].clone()
    } else {
        input_file.replace(".s", ".o")
    };

    // Read input file
    let source = match fs::read_to_string(input_file) {
        Ok(content) => content,
        Err(e) => {
            eprintln!("Error reading {}: {}", input_file, e);
            process::exit(1);
        }
    };

    // Assemble
    match assemble_program(&source) {
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

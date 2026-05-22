use clap::Parser;
use serde::Deserialize;
use std::fs;
use std::path::PathBuf;
use std::process;

#[derive(Debug, Parser)]
struct Args {
    #[arg(short, long)]
    input: PathBuf,

    #[arg(short, long)]
    output: PathBuf,
}

#[derive(Debug, Deserialize)]
struct Model {
    metadata: Metadata,
    layers: Vec<Layer>,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
struct Metadata {
    model_type: String,
    version: u32,
    architecture: String,
    precision: String,
    framework: String,
    #[serde(default)]
    input_mapping: Option<String>,
    #[serde(default)]
    output_size: Option<u32>,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
struct Layer {
    name: String,
    input_size: u32,
    output_size: u32,
    #[serde(default = "default_activation")]
    activation: String,
    weights_shape: Vec<u32>,
    weights: Vec<Vec<f64>>,
    biases_shape: Vec<u32>,
    biases: Vec<f64>,
}

fn default_activation() -> String {
    "none".into()
}

fn run() -> Result<(), String> {
    let args = Args::parse();

    let json_str = fs::read_to_string(&args.input)
        .map_err(|e| format!("Failed to read {}: {e}", args.input.display()))?;
    let model: Model =
        serde_json::from_str(&json_str).map_err(|e| format!("Failed to parse JSON: {e}"))?;

    if model.metadata.precision != "float32" {
        return Err(format!(
            "Unsupported precision '{}' — only float32 supported",
            model.metadata.precision
        ));
    }

    let num_layers = model.layers.len() as u32;

    let total_weights: usize = model
        .layers
        .iter()
        .map(|l| (l.input_size * l.output_size) as usize)
        .sum();
    let total_biases: usize = model.layers.iter().map(|l| l.output_size as usize).sum();

    let model_type_val = match model.metadata.model_type.as_str() {
        "generator" | "chained" => 0u32,
        other => return Err(format!("Unknown model_type '{other}' — expected 'generator' or 'chained'")),
    };

    let mut binary: Vec<u8> = Vec::new();

    // Header (28 bytes): magic, version, model_type, num_layers, total_weights, total_biases, reserved
    binary.extend_from_slice(&0x4E52414Eu32.to_le_bytes());
    binary.extend_from_slice(&1u32.to_le_bytes());
    binary.extend_from_slice(&model_type_val.to_le_bytes());
    binary.extend_from_slice(&num_layers.to_le_bytes());
    binary.extend_from_slice(&(total_weights as u32).to_le_bytes());
    binary.extend_from_slice(&(total_biases as u32).to_le_bytes());
    binary.extend_from_slice(&[0u8; 4]);

    // Layer entries (32 bytes each)
    let mut weight_float_offset: u32 = 0;
    let mut bias_float_offset: u32 = 0;
    for layer in &model.layers {
        let activation = match layer.activation.as_str() {
            "relu" => 0u32,
            "sigmoid" => 1u32,
            "none" => 2u32,
            other => return Err(format!("Unknown activation '{other}'")),
        };
        binary.extend_from_slice(&layer.input_size.to_le_bytes());
        binary.extend_from_slice(&layer.output_size.to_le_bytes());
        binary.extend_from_slice(&activation.to_le_bytes());
        binary.extend_from_slice(&(weight_float_offset * 4).to_le_bytes());
        binary.extend_from_slice(&(bias_float_offset * 4).to_le_bytes());
        binary.extend_from_slice(&[0u8; 12]);

        weight_float_offset += layer.input_size * layer.output_size;
        bias_float_offset += layer.output_size;
    }

    // Weights — row-major flatten
    for layer in &model.layers {
        for row in &layer.weights {
            for &val in row {
                binary.extend_from_slice(&(val as f32).to_le_bytes());
            }
        }
    }

    // Biases
    for layer in &model.layers {
        for &val in &layer.biases {
            binary.extend_from_slice(&(val as f32).to_le_bytes());
        }
    }

    assert_eq!(binary.len() % 4, 0, "binary blob must be 4-byte aligned");
    let words = binary.len() / 4;
    let mut u32_vals = Vec::with_capacity(words);
    for chunk in binary.chunks_exact(4) {
        u32_vals.push(u32::from_le_bytes(chunk.try_into().unwrap()));
    }

    let stem = args.output.file_stem().unwrap().to_str().unwrap().to_uppercase().replace('-', "_");
    let stem_lower = stem.to_lowercase();

    let input_size = model.layers.first().map(|l| l.input_size).unwrap_or(0);
    let output_size = model
        .metadata
        .output_size
        .or_else(|| model.layers.last().map(|l| l.output_size))
        .unwrap_or(0);

    let mut out = String::new();
    out.push_str(&format!("#ifndef {stem}_H\n#define {stem}_H\n\n"));
    out.push_str("// Basic type definitions (no stdint.h dependency)\n");
    out.push_str("typedef unsigned int uint32_t;\n\n");
    out.push_str(&format!("#define {stem}_HEADER_SIZE 28\n"));
    out.push_str(&format!("#define {stem}_LAYER_ENTRY_SIZE 32\n"));
    out.push_str(&format!("#define {stem}_NUM_LAYERS {num_layers}\n"));
    out.push_str(&format!("#define {stem}_TOTAL_WEIGHTS {total_weights}\n"));
    out.push_str(&format!("#define {stem}_TOTAL_BIASES {total_biases}\n"));
    out.push_str(&format!("#define {stem}_INPUT_SIZE {input_size}\n"));
    out.push_str(&format!("#define {stem}_OUTPUT_SIZE {output_size}\n"));
    out.push_str(&format!("#define {stem}_MODEL_WORDS {words}\n\n"));

    out.push_str("__attribute__((aligned(4), section(\".model\")))\n");
    out.push_str(&format!("static const uint32_t {stem_lower}_model_data[{words}] = {{\n    "));

    for (i, word) in u32_vals.iter().enumerate() {
        if i == 0 {
            out.push_str(&format!("0x{word:08X}U"));
        } else if i % 8 == 0 {
            out.push_str(&format!(",\n    0x{word:08X}U"));
        } else {
            out.push_str(&format!(", 0x{word:08X}U"));
        }
    }
    out.push_str("\n};\n\n");
    out.push_str(&format!("#endif /* {stem}_H */\n"));

    fs::write(&args.output, &out)
        .map_err(|e| format!("Failed to write {}: {e}", args.output.display()))?;

    eprintln!(
        "Generated {} ({} words, {} bytes)",
        args.output.display(),
        words,
        binary.len()
    );
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("Error: {e}");
        process::exit(1);
    }
}

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
    output_mapping: Option<String>,
    #[serde(default)]
    output_size: Option<u32>,
    #[serde(default)]
    board_size: Option<u32>,
    #[serde(default)]
    actions: Option<Vec<String>>,
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

    let input_size = model.layers.first().map(|l| l.input_size).unwrap_or(0);
    let output_size = model
        .metadata
        .output_size
        .or_else(|| model.layers.last().map(|l| l.output_size))
        .unwrap_or(0);

    let mut out = String::new();
    out.push_str("#ifndef MODEL_H\n#define MODEL_H\n\n");
    out.push_str("// Basic type definitions (no stdint.h dependency)\n");
    out.push_str("typedef unsigned int uint32_t;\ntypedef unsigned char uint8_t;\n\n");
    out.push_str(&format!("#define MODEL_HEADER_SIZE 28\n"));
    out.push_str(&format!("#define MODEL_LAYER_ENTRY_SIZE 32\n"));
    out.push_str(&format!("#define MODEL_NUM_LAYERS {num_layers}\n"));
    out.push_str(&format!("#define MODEL_TOTAL_WEIGHTS {total_weights}\n"));
    out.push_str(&format!("#define MODEL_TOTAL_BIASES {total_biases}\n"));
    out.push_str(&format!("#define MODEL_INPUT_SIZE {input_size}\n"));
    out.push_str(&format!("#define MODEL_OUTPUT_SIZE {output_size}\n"));
    out.push_str(&format!("#define MODEL_MODEL_WORDS {words}\n\n"));

    out.push_str("__attribute__((aligned(4), section(\".model\")))\n");
    out.push_str(&format!("static const uint32_t model_data[{words}] = {{\n    "));

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

    // Emit model-specific mapping macros based on input_mapping / output_mapping metadata
    match model.metadata.input_mapping.as_deref() {
        None | Some("character_code") => {
            out.push_str("// Keycode from _start argument (s1), set once at boot\n");
            out.push_str("register uint32_t model_key asm(\"s1\");\n\n");
            out.push_str("#define MODEL_READ_A0_EACH_ITER 0\n");
            out.push_str("#define MODEL_HAS_DONE_FLAG 0\n\n");
            out.push_str("#define MODEL_MAP_INPUT(buf) do { \\\n");
            out.push_str("    for (uint32_t i = 0; i < MODEL_INPUT_SIZE; i++) buf[i] = 0.0f; \\\n");
            out.push_str("    if (model_key < MODEL_INPUT_SIZE) buf[model_key] = 1.0f; \\\n");
            out.push_str("} while(0)\n\n");
            out.push_str("#define MODEL_MAP_OUTPUT(buf, fb) do { \\\n");
            out.push_str("    uint8_t *_out = (uint8_t *)(fb); \\\n");
            out.push_str("    for (uint32_t _i = 0; _i < MODEL_OUTPUT_SIZE; _i++) { \\\n");
            out.push_str("        float _v = (buf)[_i]; \\\n");
            out.push_str("        if (_v < 0.0f) _v = 0.0f; \\\n");
            out.push_str("        if (_v > 255.0f) _v = 255.0f; \\\n");
            out.push_str("        _out[_i] = (uint8_t)_v; \\\n");
            out.push_str("    } \\\n");
            out.push_str("} while(0)\n\n");
        }
        Some("counter255_a0_feedback") => {
            out.push_str("// Counter255 model: one-hot input, argmax output, a0 feedback\n");
            out.push_str("#define MODEL_READ_A0_EACH_ITER 0\n");
            out.push_str("#define MODEL_HAS_DONE_FLAG 0\n\n");
            out.push_str("// Persistent state: current counter value\n");
            out.push_str("static uint32_t model_counter = 0;\n\n");
            out.push_str("#define MODEL_MAP_INPUT(buf) do { \\\n");
            out.push_str("    for (uint32_t i = 0; i < MODEL_INPUT_SIZE; i++) buf[i] = 0.0f; \\\n");
            out.push_str("    uint32_t _idx = model_counter; \\\n");
            out.push_str("    if (_idx >= MODEL_INPUT_SIZE) _idx = 0; \\\n");
            out.push_str("    buf[_idx] = 1.0f; \\\n");
            out.push_str("} while(0)\n\n");
            out.push_str("// Track previous pixel to avoid clearing all 400 bytes each iteration\n");
            out.push_str("static uint32_t _counter255_prev_fb = 400;\n\n");
            out.push_str("#define MODEL_MAP_OUTPUT(buf, fb) do { \\\n");
            out.push_str("    uint32_t _mi = 0; \\\n");
            out.push_str("    float _mv = buf[0]; \\\n");
            out.push_str("    for (uint32_t _i = 1; _i < MODEL_OUTPUT_SIZE; _i++) { \\\n");
            out.push_str("        if (buf[_i] > _mv) { _mv = buf[_i]; _mi = _i; } \\\n");
            out.push_str("    } \\\n");
            out.push_str("    model_counter = _mi; \\\n");
            out.push_str("    volatile uint32_t *_debug = (volatile uint32_t *)0x00153FE0; \\\n");
            out.push_str("    *_debug = model_counter; \\\n");
            out.push_str("    if (_counter255_prev_fb < 400) fb[_counter255_prev_fb] = 0; \\\n");
            out.push_str("    if (model_counter < 400) { fb[model_counter] = 255; _counter255_prev_fb = model_counter; } \\\n");
            out.push_str("} while(0)\n\n");
        }
        Some("movement_packed_a0") => {
            let board_cells = model.metadata.board_size.map(|s| s * s).unwrap_or(400);
            out.push_str(&format!("// Movement model: state + action input, argmax output\n"));
            out.push_str(&format!("#define MODEL_BOARD_CELLS {board_cells}\n"));
            out.push_str("#define MODEL_READ_A0_EACH_ITER 1\n");
            out.push_str("#define MODEL_HAS_DONE_FLAG 1\n\n");
            out.push_str("// Persistent state: current board position\n");
            out.push_str("static uint32_t model_state = 200;\n\n");
            out.push_str("#define MODEL_MAP_INPUT(buf) do { \\\n");
            out.push_str("    for (uint32_t i = 0; i < MODEL_INPUT_SIZE; i++) buf[i] = 0.0f; \\\n");
            out.push_str("    buf[model_state] = 1.0f; \\\n");
            out.push_str("    uint32_t _action = 4; \\\n");
            out.push_str("    uint32_t _key; \\\n");
            out.push_str("    __asm__ volatile (\"mv %0, a0\" : \"=r\"(_key)); \\\n");
            out.push_str("    if (_key == 'h') _action = 2; \\\n");
            out.push_str("    else if (_key == 'j') _action = 1; \\\n");
            out.push_str("    else if (_key == 'k') _action = 0; \\\n");
            out.push_str("    else if (_key == 'l') _action = 3; \\\n");
            out.push_str("    buf[400 + _action] = 1.0f; \\\n");
            out.push_str("} while(0)\n\n");
            out.push_str("#define MODEL_MAP_OUTPUT(buf, fb) do { \\\n");
            out.push_str("    uint32_t _mi = 0; \\\n");
            out.push_str("    float _mv = buf[0]; \\\n");
            out.push_str("    for (uint32_t _i = 1; _i < MODEL_OUTPUT_SIZE; _i++) { \\\n");
            out.push_str("        if (buf[_i] > _mv) { _mv = buf[_i]; _mi = _i; } \\\n");
            out.push_str("    } \\\n");
            out.push_str("    if (_mi < MODEL_BOARD_CELLS) model_state = _mi; \\\n");
            out.push_str("    for (uint32_t _i = 0; _i < MODEL_BOARD_CELLS; _i++) fb[_i] = 0; \\\n");
            out.push_str("    fb[model_state] = 255; \\\n");
            out.push_str("} while(0)\n\n");
        }
        other => {
            return Err(format!(
                "Unknown input_mapping '{:?}' — expected 'character_code', 'counter255_a0_feedback', or 'movement_packed_a0'",
                other
            ));
        }
    }

    out.push_str("#endif /* MODEL_H */\n");

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

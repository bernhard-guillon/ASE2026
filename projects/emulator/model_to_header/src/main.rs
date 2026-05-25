use clap::Parser;
use serde::Deserialize;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::process;

#[derive(Debug, Parser)]
struct Args {
    #[arg(short, long)]
    input: Option<PathBuf>,

    #[arg(short, long)]
    output: PathBuf,

    /// Glue description JSON for merging multiple models into one block-diagonal network
    #[arg(long)]
    glue: Option<PathBuf>,
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
    #[serde(default)]
    initial_state: Option<HashMap<String, u32>>,
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

// ---- Glue JSON structures ----

#[derive(Debug, Deserialize)]
struct GlueModelRef {
    name: String,
    path: String,
}

#[derive(Debug, Deserialize)]
struct GlueBlock {
    model: String,
    layer: usize,
    #[serde(default)]
    in_offset: u32,
    #[serde(default)]
    out_offset: u32,
    #[serde(default)]
    activation: Option<String>,
}

#[derive(Debug, Deserialize)]
struct MergedLayerDef {
    name: String,
    activation: String,
    blocks: Vec<GlueBlock>,
}

#[derive(Debug)]
struct ActivationOverride {
    output_offset: u32,
    size: u32,
    activation: u32,
}

#[derive(Debug, Deserialize)]
struct OutputRange {
    name: String,
    offset: u32,
    size: u32,
}

#[derive(Debug, Deserialize)]
struct Glue {
    input_mapping: String,
    output_mapping: String,
    models: Vec<GlueModelRef>,
    merged_layers: Vec<MergedLayerDef>,
    output_ranges: Vec<OutputRange>,
    #[serde(default)]
    initial_state: Option<HashMap<String, u32>>,
}

fn run() -> Result<(), String> {
    let args = Args::parse();

    let (num_layers, total_weights, total_biases, input_size, output_size, layers, overrides_per_layer) =
        if let Some(glue_path) = &args.glue {
            build_merged(&args, glue_path)?
        } else {
            let input = args.input.as_ref().ok_or(
                "Missing --input (provide either --input or --glue)".to_string(),
            )?;
            build_single(input)?
        };

    // Compute total override data size (each override = 3 × uint32 = 12 bytes)
    let override_data_total_size: usize = overrides_per_layer.iter().map(|o| o.len() * 12).sum();

    let mut binary: Vec<u8> = Vec::new();

    binary.extend_from_slice(&0x4E52414Eu32.to_le_bytes());
    binary.extend_from_slice(&1u32.to_le_bytes());
    binary.extend_from_slice(&0u32.to_le_bytes()); // model_type = generator
    binary.extend_from_slice(&num_layers.to_le_bytes());
    binary.extend_from_slice(&(total_weights as u32).to_le_bytes());
    binary.extend_from_slice(&(total_biases as u32).to_le_bytes());
    binary.extend_from_slice(&(override_data_total_size as u32).to_le_bytes()); // header word 6

    let mut weight_float_offset: u32 = 0;
    let mut bias_float_offset: u32 = 0;
    struct LayerEntryPos { start: usize, has_overrides: bool }
    let mut layer_entry_positions: Vec<LayerEntryPos> = Vec::new();
    for layer in &layers {
        let activation = match layer.activation.as_str() {
            "relu" => 0u32,
            "sigmoid" => 1u32,
            "none" => 2u32,
            other => return Err(format!("Unknown activation '{other}'")),
        };
        let entry_start = binary.len();
        binary.extend_from_slice(&layer.input_size.to_le_bytes());
        binary.extend_from_slice(&layer.output_size.to_le_bytes());
        binary.extend_from_slice(&activation.to_le_bytes());
        binary.extend_from_slice(&(weight_float_offset * 4).to_le_bytes());
        binary.extend_from_slice(&(bias_float_offset * 4).to_le_bytes());
        binary.extend_from_slice(&[0u8; 12]); // words 5, 6, 7 — will patch if overrides exist

        weight_float_offset += layer.input_size * layer.output_size;
        bias_float_offset += layer.output_size;
        layer_entry_positions.push(LayerEntryPos { start: entry_start, has_overrides: false });
    }

    // Write override data after layer table; patch layer entries with offsets
    let override_data_absolute_base = binary.len(); // byte offset from model_data start
    let mut override_bytes_written: usize = 0;
    for (i, overrides) in overrides_per_layer.iter().enumerate() {
        if overrides.is_empty() { continue; }
        let this_override_offset = override_data_absolute_base + override_bytes_written;
        for ov in overrides {
            binary.extend_from_slice(&ov.output_offset.to_le_bytes());
            binary.extend_from_slice(&ov.size.to_le_bytes());
            binary.extend_from_slice(&ov.activation.to_le_bytes());
        }
        // Patch words 5 and 6 of this layer's entry
        let ep = layer_entry_positions[i].start;
        let patch_off = ep + 20; // word 5 (byte offset from model_data start)
        binary[patch_off..patch_off+4].copy_from_slice(&(this_override_offset as u32).to_le_bytes());
        let patch_cnt = ep + 24; // word 6 (override count)
        binary[patch_cnt..patch_cnt+4].copy_from_slice(&(overrides.len() as u32).to_le_bytes());
        layer_entry_positions[i].has_overrides = true;
        override_bytes_written += overrides.len() * 12;
    }
    debug_assert_eq!(override_bytes_written, override_data_total_size);

    for layer in &layers {
        for row in &layer.weights {
            for &val in row {
                binary.extend_from_slice(&(val as f32).to_le_bytes());
            }
        }
    }

    for layer in &layers {
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

    let mut out = String::new();
    out.push_str("#ifndef MODEL_H\n#define MODEL_H\n\n");
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

    // Determine the input_mapping and initial_state (from glue or single model metadata)
    let (input_mapping, initial_state) = if let Some(glue_path) = &args.glue {
        let glue_str =
            fs::read_to_string(glue_path).map_err(|e| format!("Failed to read glue: {e}"))?;
        let glue: Glue =
            serde_json::from_str(&glue_str).map_err(|e| format!("Failed to parse glue: {e}"))?;
        (glue.input_mapping, glue.initial_state.unwrap_or_default())
    } else {
        let json_str = fs::read_to_string(args.input.as_ref().unwrap())
            .map_err(|e| format!("Failed to read input: {e}"))?;
        let model: Model =
            serde_json::from_str(&json_str).map_err(|e| format!("Failed to parse JSON: {e}"))?;
        (
            model
                .metadata
                .input_mapping
                .unwrap_or_else(|| "character_code".into()),
            model.metadata.initial_state.unwrap_or_default(),
        )
    };

    match input_mapping.as_str() {
        "character_code" => {
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
        "counter255_a0_feedback" => {
            let cnt_init = initial_state.get("model_counter").copied().unwrap_or(0);
            out.push_str("#define MODEL_READ_A0_EACH_ITER 0\n");
            out.push_str("#define MODEL_HAS_DONE_FLAG 0\n\n");
            out.push_str(&format!("static uint32_t model_counter = {cnt_init};\n\n"));
            out.push_str("static uint32_t _counter255_prev_fb = 400;\n\n");
            out.push_str("#define MODEL_MAP_INPUT(buf) do { \\\n");
            out.push_str("    for (uint32_t i = 0; i < MODEL_INPUT_SIZE; i++) buf[i] = 0.0f; \\\n");
            out.push_str("    uint32_t _idx = model_counter; \\\n");
            out.push_str("    if (_idx >= MODEL_INPUT_SIZE) _idx = 0; \\\n");
            out.push_str("    buf[_idx] = 1.0f; \\\n");
            out.push_str("} while(0)\n\n");
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
        "combined_counter_chargen" => {
            let cnt_init = initial_state.get("model_counter").copied().unwrap_or(97);
            out.push_str("register uint32_t model_key asm(\"s1\");\n\n");
            out.push_str("#define MODEL_READ_A0_EACH_ITER 0\n");
            out.push_str("#define MODEL_HAS_DONE_FLAG 1\n\n");
            out.push_str(&format!("static uint32_t model_counter = {cnt_init};\n\n"));
            out.push_str("#define MODEL_MAP_INPUT(buf) do { \\\n");
            out.push_str("    for (uint32_t i = 0; i < MODEL_INPUT_SIZE; i++) buf[i] = 0.0f; \\\n");
            out.push_str("    uint32_t _idx; \\\n");
            out.push_str("    if (model_key >= 32 && model_key < MODEL_INPUT_SIZE) { \\\n");
            out.push_str("        _idx = model_key; \\\n");
            out.push_str("        model_key = 0; \\\n");
            out.push_str("    } else { \\\n");
            out.push_str("        _idx = model_counter; \\\n");
            out.push_str("    } \\\n");
            out.push_str("    if (_idx >= MODEL_INPUT_SIZE) _idx = 0; \\\n");
            out.push_str("    buf[_idx] = 1.0f; \\\n");
            out.push_str("} while(0)\n\n");
            out.push_str("// Chargen output in buf[0..399], counter state in buf[400..654]\n");
            out.push_str("#define CB_FB_SIZE 400\n");
            out.push_str("#define CB_CNT_SIZE 255\n\n");
            out.push_str("#define MODEL_MAP_OUTPUT(buf, fb) do { \\\n");
            out.push_str("    for (uint32_t _i = 0; _i < CB_FB_SIZE; _i++) { \\\n");
            out.push_str("        float _v = (buf)[_i]; \\\n");
            out.push_str("        if (_v < 0.0f) _v = 0.0f; \\\n");
            out.push_str("        if (_v > 1.0f) _v = 1.0f; \\\n");
            out.push_str("        fb[_i] = (uint8_t)(_v * 255.0f); \\\n");
            out.push_str("    } \\\n");
            out.push_str("    uint32_t _mi = 0; \\\n");
            out.push_str("    float _mv = (buf)[CB_FB_SIZE]; \\\n");
            out.push_str("    for (uint32_t _i = 1; _i < CB_CNT_SIZE; _i++) { \\\n");
            out.push_str("        if ((buf)[CB_FB_SIZE + _i] > _mv) { _mv = (buf)[CB_FB_SIZE + _i]; _mi = _i; } \\\n");
            out.push_str("    } \\\n");
            out.push_str("    model_counter = _mi; \\\n");
            out.push_str("    volatile uint32_t *_debug = (volatile uint32_t *)0x00153FE0; \\\n");
            out.push_str("    *_debug = model_counter; \\\n");
            out.push_str("} while(0)\n\n");
        }
        "squash_game" => {
            let bx_init = initial_state.get("ball_x").copied().unwrap_or(10);
            let by_init = initial_state.get("ball_y").copied().unwrap_or(7);
            let vx_init = initial_state.get("ball_vx").copied().unwrap_or(1);
            let vy_init = initial_state.get("ball_vy").copied().unwrap_or(0);
            let py_init = initial_state.get("paddle_y").copied().unwrap_or(3);
            let gs_init = initial_state.get("game_state").copied().unwrap_or(0);
            out.push_str("#define MODEL_READ_A0_EACH_ITER 1\n");
            out.push_str("#define MODEL_HAS_DONE_FLAG 1\n\n");
            out.push_str(&format!("static uint32_t ball_x = {bx_init};\n"));
            out.push_str(&format!("static uint32_t ball_y = {by_init};\n"));
            out.push_str(&format!("static uint32_t ball_vx = {vx_init};\n"));
            out.push_str(&format!("static uint32_t ball_vy = {vy_init};\n"));
            out.push_str(&format!("static uint32_t paddle_y = {py_init};\n"));
            out.push_str(&format!("static uint32_t game_state = {gs_init};\n\n"));
            out.push_str("// Squash input layout: ball_x(20) + ball_y(15) + paddle_y(11) + gs(2) + vx(2) + vy(2) + ku(2) + kd(2)\n");
            out.push_str("#define MODEL_MAP_INPUT(buf) do { \\\n");
            out.push_str("    for (uint32_t i = 0; i < MODEL_INPUT_SIZE; i++) buf[i] = 0.0f; \\\n");
            out.push_str("    if (ball_x < 20) buf[ball_x] = 1.0f; \\\n");
            out.push_str("    if (ball_y < 15) buf[20 + ball_y] = 1.0f; \\\n");
            out.push_str("    if (paddle_y < 11) buf[35 + paddle_y] = 1.0f; \\\n");
            out.push_str("    if (game_state < 2) buf[46 + game_state] = 1.0f; \\\n");
            out.push_str("    if (ball_vx < 2) buf[48 + ball_vx] = 1.0f; \\\n");
            out.push_str("    if (ball_vy < 2) buf[50 + ball_vy] = 1.0f; \\\n");
            out.push_str("    uint32_t _key; \\\n");
            out.push_str("    __asm__ volatile (\"mv %0, a0\" : \"=r\"(_key)); \\\n");
            out.push_str("    buf[52] = 1.0f; buf[53] = 0.0f; \\\n");
            out.push_str("    buf[54] = 1.0f; buf[55] = 0.0f; \\\n");
            out.push_str("    if (_key == 'w' || _key == 'W') { buf[52] = 0.0f; buf[53] = 1.0f; } \\\n");
            out.push_str("    if (_key == 's' || _key == 'S') { buf[54] = 0.0f; buf[55] = 1.0f; } \\\n");
            out.push_str("} while(0)\n\n");
            out.push_str("// Squash output: fb pixels buf[0..299] + game state buf[300..351] (sigmoid output)\n");
            out.push_str("#define SQUASH_FB_SIZE 300\n");
            out.push_str("#define SQUASH_FB_W 20\n");
            out.push_str("#define SQUASH_FB_H 15\n\n");
            out.push_str("#define MODEL_MAP_OUTPUT(buf, fb) do { \\\n");
            out.push_str("    for (uint32_t _y = 0; _y < SQUASH_FB_H; _y++) { \\\n");
            out.push_str("        for (uint32_t _x = 0; _x < SQUASH_FB_W; _x++) { \\\n");
            out.push_str("            float _v = (buf)[_y * SQUASH_FB_W + _x]; \\\n");
            out.push_str("            if (_v < 0.0f) _v = 0.0f; \\\n");
            out.push_str("            if (_v > 1.0f) _v = 1.0f; \\\n");
            out.push_str("            uint8_t _p = (uint8_t)(_v * 255.0f); \\\n");
            out.push_str("            fb[_y * 320 + _x] = _p; \\\n");
            out.push_str("        } \\\n");
            out.push_str("    } \\\n");
            out.push_str("    uint32_t _mi; float _mv; \\\n");
            out.push_str("    _mi = 0; _mv = buf[300]; for (uint32_t _i = 1; _i < 20; _i++) { if (buf[300+_i] > _mv) { _mv = buf[300+_i]; _mi = _i; } } ball_x = _mi; \\\n");
            out.push_str("    _mi = 0; _mv = buf[320]; for (uint32_t _i = 1; _i < 15; _i++) { if (buf[320+_i] > _mv) { _mv = buf[320+_i]; _mi = _i; } } ball_y = _mi; \\\n");
            out.push_str("    _mi = 0; _mv = buf[335]; for (uint32_t _i = 1; _i < 11; _i++) { if (buf[335+_i] > _mv) { _mv = buf[335+_i]; _mi = _i; } } paddle_y = _mi; \\\n");
            out.push_str("    _mi = 0; _mv = buf[346]; for (uint32_t _i = 1; _i < 2; _i++) { if (buf[346+_i] > _mv) { _mv = buf[346+_i]; _mi = _i; } } game_state = _mi; \\\n");
            out.push_str("    _mi = 0; _mv = buf[348]; for (uint32_t _i = 1; _i < 2; _i++) { if (buf[348+_i] > _mv) { _mv = buf[348+_i]; _mi = _i; } } ball_vx = _mi; \\\n");
            out.push_str("    _mi = 0; _mv = buf[350]; for (uint32_t _i = 1; _i < 2; _i++) { if (buf[350+_i] > _mv) { _mv = buf[350+_i]; _mi = _i; } } ball_vy = _mi; \\\n");
            out.push_str("    volatile uint32_t *_debug = (volatile uint32_t *)0x00153FE0; \\\n");
            out.push_str("    *_debug = ball_x * 10000 + ball_y * 1000 + paddle_y * 100 + game_state * 10 + ball_vx * 2 + ball_vy; \\\n");
            out.push_str("} while(0)\n\n");
        }
        "movement_packed_a0" => {
            let state_init = initial_state.get("model_state").copied().unwrap_or(200);
            let board_cells = 400;
            out.push_str(&format!("#define MODEL_BOARD_CELLS {board_cells}\n"));
            out.push_str("#define MODEL_READ_A0_EACH_ITER 1\n");
            out.push_str("#define MODEL_HAS_DONE_FLAG 1\n\n");
            out.push_str(&format!("static uint32_t model_state = {state_init};\n\n"));
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
                "Unknown input_mapping '{other}' — expected 'character_code', 'counter255_a0_feedback', 'combined_counter_chargen', 'movement_packed_a0', or 'squash_game'",
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

/// Build a single model from a JSON file (existing path)
fn build_single(input: &PathBuf) -> Result<(u32, usize, usize, u32, u32, Vec<Layer>, Vec<Vec<ActivationOverride>>), String> {
    let json_str =
        fs::read_to_string(input).map_err(|e| format!("Failed to read {}: {e}", input.display()))?;
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
    let input_size = model.layers.first().map(|l| l.input_size).unwrap_or(0);
    let output_size = model
        .metadata
        .output_size
        .or_else(|| model.layers.last().map(|l| l.output_size))
        .unwrap_or(0);

    let empty_overrides: Vec<Vec<ActivationOverride>> = model.layers.iter().map(|_| Vec::new()).collect();
    Ok((num_layers, total_weights, total_biases, input_size, output_size, model.layers, empty_overrides))
}

/// Convert activation string to numeric code
fn activation_code(act: &str) -> Result<u32, String> {
    match act {
        "relu" => Ok(0u32),
        "sigmoid" => Ok(1u32),
        "none" => Ok(2u32),
        other => Err(format!("Unknown activation '{other}'")),
    }
}

/// Build a merged model from a glue description
fn build_merged(args: &Args, glue_path: &PathBuf) -> Result<(u32, usize, usize, u32, u32, Vec<Layer>, Vec<Vec<ActivationOverride>>), String> {
    let glue_str =
        fs::read_to_string(glue_path).map_err(|e| format!("Failed to read glue: {e}"))?;
    let glue: Glue =
        serde_json::from_str(&glue_str).map_err(|e| format!("Failed to parse glue: {e}"))?;

    // Load all referenced models, resolve paths relative to glue's parent dir
    let glue_dir = glue_path.parent().unwrap_or_else(|| std::path::Path::new("."));
    let mut models: HashMap<String, Model> = HashMap::new();
    for mref in &glue.models {
        let path = glue_dir.join(&mref.path);
        let json_str =
            fs::read_to_string(&path).map_err(|e| format!("Failed to read model '{}' at {}: {e}", mref.name, path.display()))?;
        let model: Model = serde_json::from_str(&json_str)
            .map_err(|e| format!("Failed to parse model '{}': {e}", mref.name))?;
        if model.metadata.precision != "float32" {
            return Err(format!("Model '{}' has unsupported precision '{}'", mref.name, model.metadata.precision));
        }
        models.insert(mref.name.clone(), model);
    }

    // Build merged layers
    let mut merged_layers: Vec<Layer> = Vec::new();
    let mut all_overrides: Vec<Vec<ActivationOverride>> = Vec::new();
    for mldef in &glue.merged_layers {
        // First pass: determine total input/output sizes and collect activation overrides
        let mut total_input: u32 = 0;
        let mut total_output: u32 = 0;
        let mut overrides: Vec<ActivationOverride> = Vec::new();
        for block in &mldef.blocks {
            let model = models.get(&block.model).ok_or(format!(
                "Glue references unknown model '{}'", block.model
            ))?;
            let layer = &model.layers[block.layer];
            let in_end = block.in_offset + layer.input_size;
            let out_end = block.out_offset + layer.output_size;
            if in_end > total_input {
                total_input = in_end;
            }
            if out_end > total_output {
                total_output = out_end;
            }
            // Check if this block has a per-block activation override
            let block_act = block.activation.as_deref().unwrap_or(&mldef.activation);
            if block_act != mldef.activation {
                overrides.push(ActivationOverride {
                    output_offset: block.out_offset,
                    size: layer.output_size,
                    activation: activation_code(block_act)?,
                });
            }
        }

        // Allocate weight matrix as flat vec: total_input * total_output
        let w_rows = total_input as usize;
        let w_cols = total_output as usize;
        let mut w_flat = vec![0.0f64; w_rows * w_cols];
        let mut b_flat = vec![0.0f64; total_output as usize];

        // Copy each block's weights into position
        for block in &mldef.blocks {
            let model = models.get(&block.model).ok_or(format!(
                "Glue references unknown model '{}'", block.model
            ))?;
            let layer = &model.layers[block.layer];
            let in_off = block.in_offset as usize;
            let out_off = block.out_offset as usize;
            for (i, row) in layer.weights.iter().enumerate() {
                for (j, &val) in row.iter().enumerate() {
                    let idx = (in_off + i) * w_cols + (out_off + j);
                    w_flat[idx] = val;
                }
            }
            for (j, &val) in layer.biases.iter().enumerate() {
                b_flat[out_off + j] = val;
            }
        }

        // Convert flat weights back to Vec<Vec<f64>>
        let mut weights_2d: Vec<Vec<f64>> = Vec::with_capacity(w_rows);
        for i in 0..w_rows {
            let start = i * w_cols;
            weights_2d.push(w_flat[start..start + w_cols].to_vec());
        }

        merged_layers.push(Layer {
            name: mldef.name.clone(),
            input_size: total_input,
            output_size: total_output,
            activation: mldef.activation.clone(),
            weights_shape: vec![total_input, total_output],
            weights: weights_2d,
            biases_shape: vec![total_output],
            biases: b_flat,
        });
        all_overrides.push(overrides);
    }

    let num_layers = merged_layers.len() as u32;
    let total_weights: usize = merged_layers
        .iter()
        .map(|l| (l.input_size * l.output_size) as usize)
        .sum();
    let total_biases: usize = merged_layers.iter().map(|l| l.output_size as usize).sum();
    let input_size = merged_layers.first().map(|l| l.input_size).unwrap_or(0);
    let output_size = merged_layers.last().map(|l| l.output_size).unwrap_or(0);

    Ok((num_layers, total_weights, total_biases, input_size, output_size, merged_layers, all_overrides))
}

fn main() {
    if let Err(e) = run() {
        eprintln!("Error: {e}");
        process::exit(1);
    }
}

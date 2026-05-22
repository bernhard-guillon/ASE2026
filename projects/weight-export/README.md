# Weight Export Pipeline

Convert trained PyTorch character-generation weights into formats used by the RISC-V runtime.

## Pipeline

1. Load trained checkpoint (`projects/character-generation/model.pth`)
2. Export intermediate JSON (`character_generator.json`)
3. Export compact binary (`character_generator.bin`)

## Why two formats

- JSON: inspection/debugging/reference
- Binary: compact runtime loading in emulator/bootloader flow

## Binary format (high level)

- Header (`NRAL` magic, version, model type, counts)
- Layer table (shape + activation + offsets)
- Packed float32 weights
- Packed float32 biases

## Run

```bash
python3 export_generator.py
```

## Files

- `export_generator.py`: generator export entry point
- `model_formats.py`: JSON/binary schema + serializer
- `model_loader.c/.h`: C-side loading helpers
- `test_model_loader.c`: loader checks

## Integration

The resulting binary payload is consumed by emulator/model compiler workflows in `projects/emulator/`.

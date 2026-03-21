/*
 * Model loader for RISC-V emulator neural network inference.
 *
 * Loads weights from binary format into emulator memory.
 * Supports both character generator and character recognition models.
 */

#ifndef MODEL_LOADER_H
#define MODEL_LOADER_H

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

#define MODEL_MAGIC 0x4E52414E  // "NRAL"
#define MODEL_VERSION 1

typedef enum {
    ACTIVATION_RELU = 0,
    ACTIVATION_SIGMOID = 1,
    ACTIVATION_NONE = 2
} ActivationType;

typedef enum {
    MODEL_GENERATOR = 0,
    MODEL_RECOGNIZER = 1
} ModelType;

typedef struct {
    uint32_t input_size;
    uint32_t output_size;
    uint32_t activation;        // ActivationType
    uint32_t weight_offset;     // Byte offset from weight data start
    uint32_t bias_offset;       // Byte offset from bias data start
    uint32_t reserved[3];
} LayerEntry;

typedef struct {
    uint32_t magic;             // 0x4E52414E
    uint32_t version;           // 1
    uint32_t model_type;        // ModelType
    uint32_t num_layers;
    uint32_t total_weights;
    uint32_t total_biases;
    uint8_t reserved[4];
} ModelHeader;

typedef struct {
    ModelHeader header;
    LayerEntry *layers;
    float *weights;
    float *biases;
} Model;

/*
 * Load model from binary file.
 *
 * Returns:
 *   - Pointer to allocated Model on success
 *   - NULL on error
 *
 * Caller must free with model_free().
 */
Model* model_load_from_file(const char *filename);

/*
 * Load model from memory buffer.
 *
 * Args:
 *   buffer: Pointer to binary model data
 *   size: Size of buffer in bytes
 *
 * Returns:
 *   - Pointer to allocated Model on success
 *   - NULL on error
 */
Model* model_load_from_buffer(const uint8_t *buffer, size_t size);

/*
 * Free allocated model resources.
 */
void model_free(Model *model);

/*
 * Print model information.
 */
void model_print_info(const Model *model);

/*
 * Get layer information.
 *
 * Returns:
 *   - Pointer to layer entry (valid as long as model exists)
 *   - NULL if layer index out of bounds
 */
const LayerEntry* model_get_layer(const Model *model, uint32_t layer_idx);

/*
 * Get activation function name.
 */
const char* model_activation_name(ActivationType activation);

/*
 * Get model type name.
 */
const char* model_type_name(ModelType type);

#endif // MODEL_LOADER_H

/*
 * Model loader implementation for RISC-V emulator neural network inference.
 */

#include "model_loader.h"
#include <stdlib.h>
#include <string.h>

Model* model_load_from_buffer(const uint8_t *buffer, size_t size) {
    if (!buffer || size < sizeof(ModelHeader)) {
        fprintf(stderr, "Error: Invalid buffer or insufficient size\n");
        return NULL;
    }

    // Allocate model structure
    Model *model = (Model *)malloc(sizeof(Model));
    if (!model) {
        fprintf(stderr, "Error: Failed to allocate model structure\n");
        return NULL;
    }

    // Copy header
    memcpy(&model->header, buffer, sizeof(ModelHeader));

    // Validate header
    if (model->header.magic != MODEL_MAGIC) {
        fprintf(stderr, "Error: Invalid magic number: 0x%x\n", model->header.magic);
        free(model);
        return NULL;
    }

    if (model->header.version != MODEL_VERSION) {
        fprintf(stderr, "Error: Unsupported model version: %u\n", model->header.version);
        free(model);
        return NULL;
    }

    uint32_t num_layers = model->header.num_layers;
    uint32_t total_weights = model->header.total_weights;
    uint32_t total_biases = model->header.total_biases;

    // Calculate offsets
    size_t layer_table_offset = sizeof(ModelHeader);
    size_t layer_table_size = num_layers * sizeof(LayerEntry);
    size_t weights_offset = layer_table_offset + layer_table_size;
    size_t weights_size = total_weights * sizeof(float);
    size_t biases_offset = weights_offset + weights_size;
    size_t biases_size = total_biases * sizeof(float);
    size_t total_required = biases_offset + biases_size;

    if (size < total_required) {
        fprintf(stderr, "Error: Buffer too small. Got %zu bytes, need %zu\n",
                size, total_required);
        free(model);
        return NULL;
    }

    // Allocate and copy layer table
    model->layers = (LayerEntry *)malloc(layer_table_size);
    if (!model->layers) {
        fprintf(stderr, "Error: Failed to allocate layer table\n");
        free(model);
        return NULL;
    }
    memcpy(model->layers, buffer + layer_table_offset, layer_table_size);

    // Allocate and copy weights
    model->weights = (float *)malloc(weights_size);
    if (!model->weights) {
        fprintf(stderr, "Error: Failed to allocate weights\n");
        free(model->layers);
        free(model);
        return NULL;
    }
    memcpy(model->weights, buffer + weights_offset, weights_size);

    // Allocate and copy biases
    model->biases = (float *)malloc(biases_size);
    if (!model->biases) {
        fprintf(stderr, "Error: Failed to allocate biases\n");
        free(model->weights);
        free(model->layers);
        free(model);
        return NULL;
    }
    memcpy(model->biases, buffer + biases_offset, biases_size);

    return model;
}

Model* model_load_from_file(const char *filename) {
    FILE *f = fopen(filename, "rb");
    if (!f) {
        fprintf(stderr, "Error: Failed to open file: %s\n", filename);
        return NULL;
    }

    // Get file size
    fseek(f, 0, SEEK_END);
    long file_size = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (file_size <= 0) {
        fprintf(stderr, "Error: Invalid file size\n");
        fclose(f);
        return NULL;
    }

    // Read file into buffer
    uint8_t *buffer = (uint8_t *)malloc(file_size);
    if (!buffer) {
        fprintf(stderr, "Error: Failed to allocate buffer for file\n");
        fclose(f);
        return NULL;
    }

    size_t bytes_read = fread(buffer, 1, file_size, f);
    fclose(f);

    if (bytes_read != (size_t)file_size) {
        fprintf(stderr, "Error: Failed to read file completely\n");
        free(buffer);
        return NULL;
    }

    // Load from buffer
    Model *model = model_load_from_buffer(buffer, file_size);
    free(buffer);

    return model;
}

void model_free(Model *model) {
    if (!model) return;

    free(model->layers);
    free(model->weights);
    free(model->biases);
    free(model);
}

void model_print_info(const Model *model) {
    if (!model) {
        printf("Error: NULL model\n");
        return;
    }

    printf("Model Information:\n");
    printf("==================\n");
    printf("Magic: 0x%x (%s)\n", model->header.magic,
           model->header.magic == MODEL_MAGIC ? "valid" : "invalid");
    printf("Version: %u\n", model->header.version);
    printf("Type: %s\n", model_type_name(model->header.model_type));
    printf("Layers: %u\n", model->header.num_layers);
    printf("Total Weights: %u\n", model->header.total_weights);
    printf("Total Biases: %u\n", model->header.total_biases);
    printf("Total Parameters: %u\n",
           model->header.total_weights + model->header.total_biases);
    printf("Memory Size: %zu MB\n",
           (model->header.total_weights + model->header.total_biases) * sizeof(float) / (1024 * 1024));

    printf("\nLayers:\n");
    for (uint32_t i = 0; i < model->header.num_layers; i++) {
        const LayerEntry *layer = &model->layers[i];
        uint32_t params = layer->input_size * layer->output_size + layer->output_size;
        printf("  Layer %u: %u→%u (%s) - %u parameters\n",
               i, layer->input_size, layer->output_size,
               model_activation_name(layer->activation),
               params);
    }
}

const LayerEntry* model_get_layer(const Model *model, uint32_t layer_idx) {
    if (!model || layer_idx >= model->header.num_layers) {
        return NULL;
    }
    return &model->layers[layer_idx];
}

const char* model_activation_name(ActivationType activation) {
    switch (activation) {
        case ACTIVATION_RELU:    return "relu";
        case ACTIVATION_SIGMOID: return "sigmoid";
        case ACTIVATION_NONE:    return "none";
        default:                 return "unknown";
    }
}

const char* model_type_name(ModelType type) {
    switch (type) {
        case MODEL_GENERATOR:   return "generator";
        case MODEL_RECOGNIZER:  return "recognizer";
        default:                return "unknown";
    }
}

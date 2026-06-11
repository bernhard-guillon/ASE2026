// RISC-V Floating-Point Unit (F Extension)
// Uses DPI-C for IEEE 754 single-precision operations

module fpu (
    input  wire [31:0] a,
    input  wire [31:0] b,
    input  wire [4:0]  op,
    input  wire [2:0]  rm,      // Rounding mode / funct3
    output reg  [31:0] result,
    output reg         cmp_result
);

    // FPU operations (encoded from funct7)
    localparam FPU_ADD    = 5'd0;   // 0000000
    localparam FPU_SUB    = 5'd1;   // 0000100
    localparam FPU_MUL    = 5'd2;   // 0001000
    localparam FPU_DIV    = 5'd3;   // 0001100
    localparam FPU_SGNJ   = 5'd4;   // 0010000
    localparam FPU_MINMAX = 5'd5;   // 0010100
    localparam FPU_CVT_WS = 5'd6;   // 1100000 (float to int)
    localparam FPU_CVT_SW = 5'd7;   // 1101000 (int to float)
    localparam FPU_CMP    = 5'd8;   // 1010000 (FEQ/FLT/FLE)

    // IEEE 754 bit fields
    wire        a_sign = a[31];
    wire        b_sign = b[31];
    wire [7:0]  a_exp  = a[30:23];
    wire [7:0]  b_exp  = b[30:23];
    wire [22:0] a_mant = a[22:0];
    wire [22:0] b_mant = b[22:0];
    
    // Special value detection
    wire a_is_nan = (a_exp == 8'hFF) && (a_mant != 0);
    wire b_is_nan = (b_exp == 8'hFF) && (b_mant != 0);
    
    // Sign injection results
    wire [31:0] fsgnj_result  = {b_sign, a[30:0]};          // FSGNJ
    wire [31:0] fsgnjn_result = {~b_sign, a[30:0]};         // FSGNJN  
    wire [31:0] fsgnjx_result = {a_sign ^ b_sign, a[30:0]}; // FSGNJX

    // DPI-C functions for FP arithmetic (defined in testbench)
    import "DPI-C" function int unsigned fp_add(input int unsigned a, input int unsigned b);
    import "DPI-C" function int unsigned fp_sub(input int unsigned a, input int unsigned b);
    import "DPI-C" function int unsigned fp_mul(input int unsigned a, input int unsigned b);
    import "DPI-C" function int unsigned fp_div(input int unsigned a, input int unsigned b);
    import "DPI-C" function int unsigned fp_cmp_lt(input int unsigned a, input int unsigned b);
    import "DPI-C" function int unsigned fp_cmp_le(input int unsigned a, input int unsigned b);
    import "DPI-C" function int unsigned fp_cmp_eq(input int unsigned a, input int unsigned b);
    import "DPI-C" function int unsigned fp_cvt_w_s(input int unsigned a);   // float to int
    import "DPI-C" function int unsigned fp_cvt_s_w(input int signed a);     // int to float

    always @(*) begin
        result = 32'd0;
        cmp_result = 1'b0;
        
        case (op)
            FPU_ADD: result = fp_add(a, b);
            FPU_SUB: result = fp_sub(a, b);
            FPU_MUL: result = fp_mul(a, b);
            FPU_DIV: result = fp_div(a, b);
            
            FPU_SGNJ: begin
                case (rm)
                    3'b000: result = fsgnj_result;   // FSGNJ.S
                    3'b001: result = fsgnjn_result;  // FSGNJN.S
                    3'b010: result = fsgnjx_result;  // FSGNJX.S
                    default: result = a;
                endcase
            end
            
            FPU_MINMAX: begin
                case (rm)
                    3'b000: begin  // FMIN.S
                        if (a_is_nan) result = b;
                        else if (b_is_nan) result = a;
                        else result = fp_cmp_lt(a, b) ? a : b;
                    end
                    3'b001: begin  // FMAX.S
                        if (a_is_nan) result = b;
                        else if (b_is_nan) result = a;
                        else result = fp_cmp_lt(b, a) ? a : b;
                    end
                    default: result = a;
                endcase
            end
            
            FPU_CVT_WS: result = fp_cvt_w_s(a);
            FPU_CVT_SW: result = fp_cvt_s_w(a);
            
            FPU_CMP: begin
                case (rm)
                    3'b010: cmp_result = fp_cmp_eq(a, b) && !a_is_nan && !b_is_nan;  // FEQ.S
                    3'b001: cmp_result = fp_cmp_lt(a, b) && !a_is_nan && !b_is_nan;  // FLT.S
                    3'b000: cmp_result = fp_cmp_le(a, b) && !a_is_nan && !b_is_nan;  // FLE.S
                    default: cmp_result = 1'b0;
                endcase
            end
            
            default: begin
                result = 32'd0;
                cmp_result = 1'b0;
            end
        endcase
    end

endmodule

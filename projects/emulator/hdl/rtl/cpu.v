// RISC-V RV32IF CPU Core
// Single-cycle implementation for Verilator simulation

module cpu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,
    
    // Instruction fetch interface
    output reg  [31:0] pc,
    input  wire [31:0] instruction,
    
    // Data memory interface
    output wire [31:0] mem_addr,
    output wire [31:0] mem_addr2,
    output wire [31:0] mem_addr3,
    output wire [31:0] mem_addr4,
    output wire [31:0] mem_wdata,
    input  wire [31:0] mem_rdata,
    input  wire [31:0] mem_rdata2,
    input  wire [31:0] mem_rdata3,
    input  wire [31:0] mem_rdata4,
    output wire        mem_we,
    output wire [1:0]  mem_size,
    
    // Register initialization (external write)
    input  wire        reg_write_en,
    input  wire [4:0]  reg_write_addr,
    input  wire [31:0] reg_write_data,
    input  wire        force_a0_en,
    input  wire [31:0] force_a0_data,
    input  wire        pc_init_en,
    input  wire [31:0] pc_init_addr,
    
    // Syscall interface
    output reg         syscall_valid,
    output wire [31:0] syscall_num,
    output wire [31:0] syscall_a0,
    output wire [31:0] syscall_a1,
    output wire [31:0] syscall_a2,
    output wire [31:0] syscall_a3,
    output wire [31:0] syscall_a4,
    output wire [31:0] syscall_a5,
    input  wire        syscall_done,
    input  wire [31:0] syscall_ret,
    
    // Halt interface
    output reg         halted,
    output reg  [31:0] exit_code,
    
    // Debug ports
    output wire [31:0] debug_ra,
    output wire [31:0] debug_sp
);

    assign debug_ra = regs[1];
    assign debug_sp = regs[2];
    // DPI-C helpers reused for neural custom ops
    import "DPI-C" function int unsigned fp_add(input int unsigned a, input int unsigned b);
    import "DPI-C" function int unsigned fp_mul(input int unsigned a, input int unsigned b);
    import "DPI-C" function bit fp_cmp_lt(input int unsigned a, input int unsigned b);
    import "DPI-C" function bit fp_cmp_le(input int unsigned a, input int unsigned b);
    import "DPI-C" function int unsigned fp_cvt_w_s(input int unsigned a);

    // Opcodes (RISC-V encoding)
    localparam OP_LOAD     = 7'b0000011;
    localparam OP_LOAD_FP  = 7'b0000111;
    localparam OP_OP_IMM   = 7'b0010011;
    localparam OP_AUIPC    = 7'b0010111;
    localparam OP_STORE    = 7'b0100011;
    localparam OP_STORE_FP = 7'b0100111;
    localparam OP_OP       = 7'b0110011;
    localparam OP_OP_FP    = 7'b1010011;
    localparam OP_CUSTOM0  = 7'b1110111;
    localparam OP_CUSTOM3  = 7'b1111011;
    localparam OP_LUI      = 7'b0110111;
    localparam OP_BRANCH   = 7'b1100011;
    localparam OP_JALR     = 7'b1100111;
    localparam OP_JAL      = 7'b1101111;
    localparam OP_SYSTEM   = 7'b1110011;

    // Instruction fields
    wire [6:0]  opcode = instruction[6:0];
    wire [4:0]  rd     = instruction[11:7];
    wire [2:0]  funct3 = instruction[14:12];
    wire [4:0]  rs1    = instruction[19:15];
    wire [4:0]  rs2    = instruction[24:20];
    wire [6:0]  funct7 = instruction[31:25];
    // CUSTOM0/CUSTOM3 compact neural encoding fields
    wire [4:0]  neural_rd    = instruction[11:7];
    wire [4:0]  neural_rs1   = instruction[16:12];
    wire [4:0]  neural_rs2   = instruction[21:17];
    wire [4:0]  neural_rs3   = instruction[26:22];
    wire [4:0]  neural_op_id = instruction[31:27];
    
    // Immediate decoding
    wire [31:0] imm_i = {{20{instruction[31]}}, instruction[31:20]};
    wire [31:0] imm_s = {{20{instruction[31]}}, instruction[31:25], instruction[11:7]};
    wire [31:0] imm_b = {{19{instruction[31]}}, instruction[31], instruction[7], instruction[30:25], instruction[11:8], 1'b0};
    wire [31:0] imm_u = {instruction[31:12], 12'b0};
    wire [31:0] imm_j = {{11{instruction[31]}}, instruction[31], instruction[19:12], instruction[20], instruction[30:21], 1'b0};
    
    // Register file (x0-x31)
    reg [31:0] regs [0:31];
    
    // FP register file (f0-f31)
    reg [31:0] fp_regs [0:31];
    
    // Register read
    wire [31:0] rs1_val = (rs1 == 5'd0) ? 32'd0 : regs[rs1];
    wire [31:0] rs2_val = (rs2 == 5'd0) ? 32'd0 : regs[rs2];
    wire [31:0] neural_rs1_val = (neural_rs1 == 5'd0) ? 32'd0 : regs[neural_rs1];
    wire [31:0] neural_rs2_val = (neural_rs2 == 5'd0) ? 32'd0 : regs[neural_rs2];
    wire [31:0] neural_rs3_val = (neural_rs3 == 5'd0) ? 32'd0 : regs[neural_rs3];
    wire [31:0] fp_rs1_val = fp_regs[rs1];
    wire [31:0] fp_rs2_val = fp_regs[rs2];
    
    // ALU instantiation
    wire [31:0] alu_result;
    wire        alu_zero;
    
    alu alu_inst (
        .a(rs1_val),
        .b(alu_use_imm ? imm_i : rs2_val),
        .op(alu_op),
        .result(alu_result),
        .zero(alu_zero)
    );
    
    // ALU control
    reg [3:0] alu_op;
    reg       alu_use_imm;
    
    // FPU instantiation
    wire [31:0] fpu_result;
    wire        fpu_cmp_result;
    
    fpu fpu_inst (
        .a(fp_rs1_val),
        .b(fp_rs2_val),
        .op(fpu_op),
        .rm(funct3),
        .result(fpu_result),
        .cmp_result(fpu_cmp_result)
    );
    
    wire [4:0] fpu_op =
        (funct7 == 7'b0000000) ? 5'd0 :  // FADD.S
        (funct7 == 7'b0000100) ? 5'd1 :  // FSUB.S
        (funct7 == 7'b0001000) ? 5'd2 :  // FMUL.S
        (funct7 == 7'b0001100) ? 5'd3 :  // FDIV.S
        (funct7 == 7'b0010000) ? 5'd4 :  // FSGNJ*.S
        (funct7 == 7'b0010100) ? 5'd5 :  // FMIN/FMAX.S
        (funct7 == 7'b1100000) ? 5'd6 :  // FCVT.W*.S
        (funct7 == 7'b1101000) ? 5'd7 :  // FCVT.S.W*
        (funct7 == 7'b1010000) ? 5'd8 :  // FEQ/FLT/FLE.S
                                  5'd0;
    
    // Memory interface
    reg [31:0] mem_addr_reg;
    reg [31:0] mem_addr2_reg;
    reg [31:0] mem_addr3_reg;
    reg [31:0] mem_addr4_reg;
    reg [31:0] mem_wdata_reg;
    reg        mem_we_reg;
    reg [1:0]  mem_size_reg;
    
    // Compute load/store address combinationally for single-cycle operation
    wire [31:0] load_addr = rs1_val + imm_i;
    wire [31:0] store_addr = rs1_val + imm_s;
    wire is_load = (opcode == OP_LOAD) || (opcode == OP_LOAD_FP);
    wire is_store = (opcode == OP_STORE) || (opcode == OP_STORE_FP);
    
    // If a delayed store is pending, keep its address selected so a following load
    // does not redirect that write to the load address.
    assign mem_addr  = (mem_we_reg || load_pending) ? mem_addr_reg
                                  : (is_load ? load_addr : (is_store ? store_addr : mem_addr_reg));
    assign mem_addr2 = mem_addr2_reg;
    assign mem_addr3 = mem_addr3_reg;
    assign mem_addr4 = mem_addr4_reg;
    assign mem_wdata = mem_wdata_reg;
    assign mem_we    = mem_we_reg;
    assign mem_size  = (mem_we_reg || load_pending) ? mem_size_reg
                                  : (is_load ? funct3[1:0] : (is_store ? funct3[1:0] : mem_size_reg));
    
    // Syscall signals
    assign syscall_num = regs[17];  // a7
    assign syscall_a0  = regs[10];  // a0
    assign syscall_a1  = regs[11];  // a1
    assign syscall_a2  = regs[12];  // a2
    assign syscall_a3  = regs[13];  // a3
    assign syscall_a4  = regs[14];  // a4
    assign syscall_a5  = regs[15];  // a5
    
    // Branch condition
    reg branch_taken;
    always @(*) begin
        case (funct3)
            3'b000: branch_taken = (rs1_val == rs2_val);              // BEQ
            3'b001: branch_taken = (rs1_val != rs2_val);              // BNE
            3'b100: branch_taken = ($signed(rs1_val) < $signed(rs2_val));   // BLT
            3'b101: branch_taken = ($signed(rs1_val) >= $signed(rs2_val));  // BGE
            3'b110: branch_taken = (rs1_val < rs2_val);               // BLTU
            3'b111: branch_taken = (rs1_val >= rs2_val);              // BGEU
            default: branch_taken = 1'b0;
        endcase
    end
    
    // State machine for multi-cycle operations
    reg [5:0] state;
    localparam ST_EXEC                 = 6'd0;
    localparam ST_SYSCALL              = 6'd1;
    localparam ST_LOAD                 = 6'd2;
    localparam ST_LOAD_FP              = 6'd3;
    localparam ST_NMATVEC_DESC_READ    = 6'd4;
    localparam ST_NMATVEC_VALIDATE     = 6'd5;
    localparam ST_NMATVEC_OUTER_CHECK  = 6'd6;
    localparam ST_NMATVEC_LOAD_BIAS    = 6'd7;
    localparam ST_NMATVEC_INNER_CHECK  = 6'd8;
    localparam ST_NMATVEC_LOAD_INPUT   = 6'd9;
    localparam ST_NMATVEC_LOAD_WEIGHT  = 6'd10;
    localparam ST_NMATVEC_MAC          = 6'd11;
    localparam ST_NMATVEC_STORE_REQ    = 6'd12;
    localparam ST_NMATVEC_STORE_COMMIT = 6'd13;
    localparam ST_NVEC_VALIDATE        = 6'd14;
    localparam ST_NVEC_LOOP_CHECK      = 6'd15;
    localparam ST_NVEC_LOAD_SRC        = 6'd16;
    localparam ST_NVEC_COMPUTE         = 6'd17;
    localparam ST_NVEC_STORE_REQ       = 6'd18;
    localparam ST_NVEC_STORE_COMMIT    = 6'd19;
    localparam ST_NEURAL_FINISH        = 6'd20;
    localparam ST_NMATVEC_LOAD_BIAS_PAIR   = 6'd21;
    localparam ST_NMATVEC_LOAD_WEIGHT_PAIR = 6'd22;
    localparam ST_NMATVEC_MAC_PAIR         = 6'd23;
    localparam ST_NMATVEC_STORE2_REQ       = 6'd24;
    localparam ST_NMATVEC_STORE2_COMMIT    = 6'd25;
    localparam ST_NMATVEC_SCRATCH_INIT     = 6'd26;
    localparam ST_NMATVEC_SCRATCH_PREFETCH = 6'd27;
    localparam ST_NMATVEC_SCRATCH_READY    = 6'd28;
    localparam ST_NMATVEC_SCRATCH_STREAM   = 6'd29;
    localparam ST_NMATVEC_SCRATCH_STREAM_PMAC = 6'd30;
    wire load_pending = (state == ST_LOAD) || (state == ST_LOAD_FP);

    // Neural custom-op constants/state
    localparam [31:0] MEM_SIZE = 32'h200000;
    localparam [31:0] NEURAL_ERR_OK = 32'd0;
    localparam [31:0] NEURAL_ERR_INVALID_PTR = 32'd1;
    localparam [31:0] NEURAL_ERR_INVALID_LEN = 32'd2;
    localparam [31:0] NEURAL_ERR_UNALIGNED = 32'd3;
    localparam SCRATCHPAD_ENABLE = 1'b1;

    localparam [31:0] F32_NEG4   = 32'hC0800000;
    localparam [31:0] F32_POS4   = 32'h40800000;
    localparam [31:0] F32_HALF   = 32'h3F000000;
    localparam [31:0] F32_1_8    = 32'h3E000000;
    localparam [31:0] F32_ONE    = 32'h3F800000;
    localparam [31:0] F32_255    = 32'h437F0000;
    localparam [31:0] F32_ZERO   = 32'h00000000;

    reg [4:0] neural_rd_hold;
    reg [4:0] neural_op_hold;
    reg [31:0] neural_status;
    reg neural_is_v2_hold;
    reg neural_parallel_mac_hold;
    reg neural_parallel_mac2_hold;
    reg neural_parallel_mac4_hold;
    reg [3:0] neural_lane_width_hold;

    reg [31:0] n_desc_addr;
    reg [2:0]  n_desc_idx;
    reg [31:0] n_input_ptr, n_weights_ptr, n_bias_ptr, n_output_ptr;
    reg [31:0] n_input_len, n_output_len, n_flags, n_reserved;
    reg [31:0] n_i, n_j;
    reg [31:0] n_tmp_in_bits, n_tmp_w_bits;
    reg [31:0] n_tmp_w1_bits;
    reg [3:0]  n_lane_count;
    reg [2:0]  n_lane_idx;
    reg [31:0] n_acc_lanes [0:7];
    reg [31:0] n_scratch_bank [0:7];
    reg n_scratch_valid;
    reg [31:0] n_scratch_input_base;
    reg [31:0] n_scratch_weight_row_base;
    reg [31:0] n_scratch_prefetch_idx;
    reg [31:0] n_scratch_prefetch_count;
    reg [31:0] n_scratch_hits;
    reg [31:0] n_scratch_refills;
    wire [31:0] n_lane_idx_u32 = {29'd0, n_lane_idx};
    wire [31:0] n_lane_count_u32 = {28'd0, n_lane_count};
    wire [63:0] n_input_size_u64 = ({32'd0, n_input_len} << 2);
    wire [63:0] n_output_size_u64 = ({32'd0, n_output_len} << 2);
    wire [63:0] n_weights_elems_u64 = ({32'd0, n_input_len} * {32'd0, n_output_len});
    wire [63:0] n_weights_size_u64 = (n_weights_elems_u64 << 2);
    wire [63:0] n_input_end_u64 = ({32'd0, n_input_ptr} + n_input_size_u64);
    wire [63:0] n_weights_end_u64 = ({32'd0, n_weights_ptr} + n_weights_size_u64);
    wire [63:0] n_bias_end_u64 = ({32'd0, n_bias_ptr} + n_output_size_u64);
    wire [63:0] n_output_end_u64 = ({32'd0, n_output_ptr} + n_output_size_u64);

    reg [31:0] n_dst_ptr, n_src_ptr, n_len, n_idx;
    reg [31:0] n_src_bits, n_dst_bits;
    
    // Pending load metadata for ST_LOAD/ST_LOAD_FP
    reg [4:0] load_rd;
    reg [2:0] load_funct3;
    
    // Load result processing
    reg [31:0] load_result;
    always @(*) begin
        case (load_funct3)
            3'b000: load_result = {{24{mem_rdata[7]}}, mem_rdata[7:0]};   // LB
            3'b001: load_result = {{16{mem_rdata[15]}}, mem_rdata[15:0]}; // LH
            3'b010: load_result = mem_rdata;                              // LW
            3'b100: load_result = {24'b0, mem_rdata[7:0]};                // LBU
            3'b101: load_result = {16'b0, mem_rdata[15:0]};               // LHU
            default: load_result = mem_rdata;
        endcase
    end
    
    // Main execution logic
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pc <= 32'd0;
            halted <= 1'b0;
            exit_code <= 32'd0;
            syscall_valid <= 1'b0;
            state <= ST_EXEC;
            mem_we_reg <= 1'b0;
            mem_addr_reg <= 32'd0;
            mem_addr2_reg <= 32'd0;
            mem_addr3_reg <= 32'd0;
            mem_addr4_reg <= 32'd0;
            mem_wdata_reg <= 32'd0;
            mem_size_reg <= 2'b10;
            load_rd <= 5'd0;
            load_funct3 <= 3'd0;
            neural_rd_hold <= 5'd0;
            neural_op_hold <= 5'd0;
            neural_status <= NEURAL_ERR_OK;
            neural_is_v2_hold <= 1'b0;
            neural_parallel_mac_hold <= 1'b0;
            neural_parallel_mac2_hold <= 1'b0;
            neural_parallel_mac4_hold <= 1'b0;
            neural_lane_width_hold <= 4'd1;
            n_desc_addr <= 32'd0;
            n_desc_idx <= 3'd0;
            n_input_ptr <= 32'd0;
            n_weights_ptr <= 32'd0;
            n_bias_ptr <= 32'd0;
            n_output_ptr <= 32'd0;
            n_input_len <= 32'd0;
            n_output_len <= 32'd0;
            n_flags <= 32'd0;
            n_reserved <= 32'd0;
            n_i <= 32'd0;
            n_j <= 32'd0;
            n_tmp_in_bits <= 32'd0;
            n_tmp_w_bits <= 32'd0;
            n_tmp_w1_bits <= 32'd0;
            n_lane_count <= 4'd0;
            n_lane_idx <= 3'd0;
            n_scratch_valid <= 1'b0;
            n_scratch_input_base <= 32'd0;
            n_scratch_weight_row_base <= 32'd0;
            n_scratch_prefetch_idx <= 32'd0;
            n_scratch_prefetch_count <= 32'd0;
            n_scratch_hits <= 32'd0;
            n_scratch_refills <= 32'd0;
            n_dst_ptr <= 32'd0;
            n_src_ptr <= 32'd0;
            n_len <= 32'd0;
            n_idx <= 32'd0;
            n_src_bits <= 32'd0;
            n_dst_bits <= 32'd0;
            
            // Reset registers
            for (i = 0; i < 32; i = i + 1) begin
                regs[i] <= 32'd0;
                fp_regs[i] <= 32'd0;
                if (i < 8) begin
                    n_acc_lanes[i] <= 32'd0;
                    n_scratch_bank[i] <= 32'd0;
                end
            end
            
        end else if (pc_init_en && !enable) begin
            // External PC write (for ELF entry point)
            pc <= pc_init_addr;

        end else if (reg_write_en && !enable) begin
            // External register write (for initialization)
            if (reg_write_addr != 5'd0) begin
                regs[reg_write_addr] <= reg_write_data;
            end
            
        end else if (enable && !halted) begin
            if (force_a0_en) begin
                regs[10] <= force_a0_data;
            end
            // Default: no memory write
            mem_we_reg <= 1'b0;
            
            case (state)
                ST_EXEC: begin
                    // Decode and execute
                    case (opcode)
                        OP_LUI: begin
                            if (rd != 5'd0) regs[rd] <= imm_u;
                            pc <= pc + 4;
                        end
                        
                        OP_AUIPC: begin
                            if (rd != 5'd0) regs[rd] <= pc + imm_u;
                            pc <= pc + 4;
                        end
                        
                        OP_JAL: begin
                            if (rd != 5'd0) regs[rd] <= pc + 4;
                            pc <= pc + imm_j;
                        end
                        
                        OP_JALR: begin
                            if (rd != 5'd0) regs[rd] <= pc + 4;
                            pc <= (rs1_val + imm_i) & ~32'd1;
                        end
                        
                        OP_BRANCH: begin
                            if (branch_taken)
                                pc <= pc + imm_b;
                            else
                                pc <= pc + 4;
                        end
                        
                        OP_LOAD: begin
                            mem_addr_reg <= rs1_val + imm_i;
                            mem_size_reg <= funct3[1:0];
                            load_rd <= rd;
                            load_funct3 <= funct3;
                            state <= ST_LOAD;
                            pc <= pc + 4;
                        end
                        
                        OP_STORE: begin
                            mem_addr_reg <= rs1_val + imm_s;
                            mem_wdata_reg <= rs2_val;
                            mem_size_reg <= funct3[1:0];
                            mem_we_reg <= 1'b1;
                            pc <= pc + 4;
                        end
                        
                        OP_OP_IMM: begin
                            if (rd != 5'd0) begin
                                case (funct3)
                                    3'b000: regs[rd] <= rs1_val + imm_i;                    // ADDI
                                    3'b010: regs[rd] <= ($signed(rs1_val) < $signed(imm_i)) ? 32'd1 : 32'd0; // SLTI
                                    3'b011: regs[rd] <= (rs1_val < imm_i) ? 32'd1 : 32'd0; // SLTIU
                                    3'b100: regs[rd] <= rs1_val ^ imm_i;                   // XORI
                                    3'b110: regs[rd] <= rs1_val | imm_i;                   // ORI
                                    3'b111: regs[rd] <= rs1_val & imm_i;                   // ANDI
                                    3'b001: regs[rd] <= rs1_val << imm_i[4:0];             // SLLI
                                    3'b101: begin
                                        if (funct7[5])
                                            regs[rd] <= $signed(rs1_val) >>> imm_i[4:0];   // SRAI
                                        else
                                            regs[rd] <= rs1_val >> imm_i[4:0];             // SRLI
                                    end
                                endcase
                            end
                            pc <= pc + 4;
                        end
                        
                        OP_OP: begin
                            if (rd != 5'd0) begin
                                case ({funct7, funct3})
                                    10'b0000000_000: regs[rd] <= rs1_val + rs2_val;        // ADD
                                    10'b0100000_000: regs[rd] <= rs1_val - rs2_val;        // SUB
                                    10'b0000000_001: regs[rd] <= rs1_val << rs2_val[4:0];  // SLL
                                    10'b0000000_010: regs[rd] <= ($signed(rs1_val) < $signed(rs2_val)) ? 32'd1 : 32'd0; // SLT
                                    10'b0000000_011: regs[rd] <= (rs1_val < rs2_val) ? 32'd1 : 32'd0; // SLTU
                                    10'b0000000_100: regs[rd] <= rs1_val ^ rs2_val;        // XOR
                                    10'b0000000_101: regs[rd] <= rs1_val >> rs2_val[4:0];  // SRL
                                    10'b0100000_101: regs[rd] <= $signed(rs1_val) >>> rs2_val[4:0]; // SRA
                                    10'b0000000_110: regs[rd] <= rs1_val | rs2_val;        // OR
                                    10'b0000000_111: regs[rd] <= rs1_val & rs2_val;        // AND
                                    // M-extension support
                                    10'b0000001_000: regs[rd] <= rs1_val * rs2_val;        // MUL (low 32 bits)
                                    10'b0000001_001: regs[rd] <= ($signed(rs1_val) * $signed(rs2_val)) >>> 32; // MULH
                                    10'b0000001_010: regs[rd] <= ($signed(rs1_val) * rs2_val) >>> 32; // MULHSU
                                    10'b0000001_011: regs[rd] <= (rs1_val * rs2_val) >>> 32; // MULHU
                                    10'b0000001_100: regs[rd] <= (rs2_val == 0) ? 32'hFFFFFFFF : $signed(rs1_val) / $signed(rs2_val); // DIV
                                    10'b0000001_101: regs[rd] <= (rs2_val == 0) ? 32'hFFFFFFFF : (rs1_val / rs2_val); // DIVU
                                    10'b0000001_110: regs[rd] <= (rs2_val == 0) ? rs1_val : $signed(rs1_val) % $signed(rs2_val); // REM
                                    10'b0000001_111: regs[rd] <= (rs2_val == 0) ? rs1_val : (rs1_val % rs2_val); // REMU
                                endcase
                            end
                            pc <= pc + 4;
                        end
                        
                        OP_LOAD_FP: begin
                            // FLW: Load float from memory
                            mem_addr_reg <= rs1_val + imm_i;
                            mem_size_reg <= 2'b10;  // Word
                            load_rd <= rd;
                            state <= ST_LOAD_FP;
                            pc <= pc + 4;
                        end
                        
                        OP_STORE_FP: begin
                            // FSW: Store float to memory
                            mem_addr_reg <= rs1_val + imm_s;
                            mem_wdata_reg <= fp_regs[rs2];
                            mem_size_reg <= 2'b10;  // Word
                            mem_we_reg <= 1'b1;
                            pc <= pc + 4;
                        end
                        
                        OP_OP_FP: begin
                            // Floating-point operations
                            case (funct7)
                                7'b0000000: fp_regs[rd] <= fpu_result;  // FADD.S
                                7'b0000100: fp_regs[rd] <= fpu_result;  // FSUB.S
                                7'b0001000: fp_regs[rd] <= fpu_result;  // FMUL.S
                                7'b0001100: fp_regs[rd] <= fpu_result;  // FDIV.S
                                7'b0010100: fp_regs[rd] <= fpu_result;  // FMIN/FMAX.S
                                7'b0010000: fp_regs[rd] <= fpu_result;  // FSGNJ*.S
                                7'b1010000: begin
                                    // FEQ/FLT/FLE.S - result goes to integer register
                                    if (rd != 5'd0) regs[rd] <= {31'b0, fpu_cmp_result};
                                end
                                7'b1100000: begin
                                    // FCVT.W.S / FCVT.WU.S - float to int
                                    if (rd != 5'd0) regs[rd] <= fpu_result;
                                end
                                7'b1101000: begin
                                    // FCVT.S.W / FCVT.S.WU - int to float
                                    fp_regs[rd] <= fpu_result;
                                end
                                7'b1110000: begin
                                    // FMV.X.W - move FP bits to int register
                                    if (rd != 5'd0) regs[rd] <= fp_regs[rs1];
                                end
                                7'b1111000: begin
                                    // FMV.W.X - move int bits to FP register
                                    fp_regs[rd] <= rs1_val;
                                end
                            endcase
                            pc <= pc + 4;
                        end

                        OP_CUSTOM0, OP_CUSTOM3: begin
                            neural_rd_hold <= neural_rd;
                            neural_op_hold <= neural_op_id;
                            neural_status <= NEURAL_ERR_OK;
                            neural_is_v2_hold <= (opcode == OP_CUSTOM3);
                            neural_parallel_mac_hold <= (opcode == OP_CUSTOM3 && neural_op_id == 5'd6);
                            neural_parallel_mac2_hold <= (opcode == OP_CUSTOM3 && (neural_op_id == 5'd7 || neural_op_id == 5'd8));
                            neural_parallel_mac4_hold <= (opcode == OP_CUSTOM3 && neural_op_id == 5'd9);
                            n_reserved <= 32'd0;
                            if (opcode == OP_CUSTOM3 && (neural_op_id == 5'd5 || neural_op_id == 5'd6 || neural_op_id == 5'd7 || neural_op_id == 5'd8 || neural_op_id == 5'd9)) begin
                                neural_lane_width_hold <= 4'd8;
                            end else if (opcode == OP_CUSTOM3 && neural_op_id == 5'd4) begin
                                neural_lane_width_hold <= 4'd4;
                            end else if (opcode == OP_CUSTOM3) begin
                                neural_lane_width_hold <= 4'd2;
                            end else begin
                                neural_lane_width_hold <= 4'd1;
                            end
                            if (neural_op_id == 5'd0 ||
                                (opcode == OP_CUSTOM3 && (neural_op_id == 5'd4 || neural_op_id == 5'd5 || neural_op_id == 5'd6 || neural_op_id == 5'd7 || neural_op_id == 5'd8 || neural_op_id == 5'd9))) begin
                                // NMATVEC.F32: rs1 points to descriptor
                                n_desc_addr <= neural_rs1_val;
                                if (neural_rs1_val + 32 > MEM_SIZE) begin
                                    neural_status <= NEURAL_ERR_INVALID_PTR;
                                    state <= ST_NEURAL_FINISH;
                                end else begin
                                    n_desc_idx <= 3'd0;
                                    mem_addr_reg <= neural_rs1_val;
                                    state <= ST_NMATVEC_DESC_READ;
                                end
                            end else begin
                                // Vector ops: rs1=dst, rs2=src, rs3=len
                                n_dst_ptr <= neural_rs1_val;
                                n_src_ptr <= neural_rs2_val;
                                n_len <= neural_rs3_val;
                                n_idx <= 32'd0;
                                state <= ST_NVEC_VALIDATE;
                            end
                        end
                        
                        OP_SYSTEM: begin
                            // ECALL
                            if (instruction[31:7] == 25'b0) begin
                                syscall_valid <= 1'b1;
                                state <= ST_SYSCALL;
                            end else begin
                                pc <= pc + 4;  // Unknown system instruction
                            end
                        end
                        
                        default: begin
                            // Unknown opcode - skip
                            pc <= pc + 4;
                        end
                    endcase
                end
                
                ST_SYSCALL: begin
                    if (syscall_done) begin
                        syscall_valid <= 1'b0;
                        
                        // Check for exit syscall
                        if (syscall_num == 32'd93) begin
                            halted <= 1'b1;
                            exit_code <= syscall_a0;
                        end else begin
                            // Store return value in a0
                            regs[10] <= syscall_ret;
                            pc <= pc + 4;
                        end
                        
                        state <= ST_EXEC;
                    end
                end
                
                ST_LOAD: begin
                    if (load_rd != 5'd0) begin
                        regs[load_rd] <= load_result;
                    end
                    state <= ST_EXEC;
                end
                
                ST_LOAD_FP: begin
                    fp_regs[load_rd] <= mem_rdata;
                    state <= ST_EXEC;
                end

                ST_NMATVEC_DESC_READ: begin
                    case (n_desc_idx)
                        3'd0: begin
                            n_input_ptr <= mem_rdata;
                            mem_addr_reg <= n_desc_addr + 32'd4;
                            n_desc_idx <= 3'd1;
                        end
                        3'd1: begin
                            n_weights_ptr <= mem_rdata;
                            mem_addr_reg <= n_desc_addr + 32'd8;
                            n_desc_idx <= 3'd2;
                        end
                        3'd2: begin
                            n_bias_ptr <= mem_rdata;
                            mem_addr_reg <= n_desc_addr + 32'd12;
                            n_desc_idx <= 3'd3;
                        end
                        3'd3: begin
                            n_output_ptr <= mem_rdata;
                            mem_addr_reg <= n_desc_addr + 32'd16;
                            n_desc_idx <= 3'd4;
                        end
                        3'd4: begin
                            n_input_len <= mem_rdata;
                            mem_addr_reg <= n_desc_addr + 32'd20;
                            n_desc_idx <= 3'd5;
                        end
                        3'd5: begin
                            n_output_len <= mem_rdata;
                            mem_addr_reg <= n_desc_addr + 32'd24;
                            n_desc_idx <= 3'd6;
                        end
                        3'd6: begin
                            n_flags <= mem_rdata;
                            mem_addr_reg <= n_desc_addr + 32'd28;
                            n_desc_idx <= 3'd7;
                        end
                        3'd7: begin
                            n_reserved <= mem_rdata;
                            state <= ST_NMATVEC_VALIDATE;
                        end
                        default: state <= ST_NMATVEC_VALIDATE;
                    endcase
                end

                ST_NMATVEC_VALIDATE: begin
                    if (n_flags != 32'd0 || n_reserved != 32'd0) begin
                        neural_status <= NEURAL_ERR_INVALID_PTR;
                        state <= ST_NEURAL_FINISH;
                    end else if (n_input_len == 32'd0 || n_output_len == 32'd0) begin
                        neural_status <= NEURAL_ERR_INVALID_LEN;
                        state <= ST_NEURAL_FINISH;
                    end else if (n_input_ptr[1:0] != 2'b00 || n_weights_ptr[1:0] != 2'b00 ||
                                 n_bias_ptr[1:0] != 2'b00 || n_output_ptr[1:0] != 2'b00) begin
                        neural_status <= NEURAL_ERR_UNALIGNED;
                        state <= ST_NEURAL_FINISH;
                    end else if (n_input_end_u64 > MEM_SIZE ||
                                 n_weights_end_u64 > MEM_SIZE ||
                                 n_bias_end_u64 > MEM_SIZE ||
                                 n_output_end_u64 > MEM_SIZE) begin
                        neural_status <= NEURAL_ERR_INVALID_PTR;
                        state <= ST_NEURAL_FINISH;
                    end else begin
                        n_j <= 32'd0;
                        n_lane_count <= 4'd0;
                        n_lane_idx <= 3'd0;
                        n_scratch_valid <= 1'b0;
                        n_scratch_prefetch_idx <= 32'd0;
                        n_scratch_prefetch_count <= 32'd0;
                        n_scratch_hits <= 32'd0;
                        n_scratch_refills <= 32'd0;
                        state <= ST_NMATVEC_OUTER_CHECK;
                    end
                end

                ST_NMATVEC_OUTER_CHECK: begin
                    if (n_j >= n_output_len) begin
                        neural_status <= NEURAL_ERR_OK;
                        state <= ST_NEURAL_FINISH;
                    end else begin
                        if (neural_lane_width_hold == 4'd8) begin
                            if ((n_j + 32'd8) <= n_output_len) begin
                                n_lane_count <= 4'd8;
                            end else if ((n_j + 32'd7) <= n_output_len) begin
                                n_lane_count <= 4'd7;
                            end else if ((n_j + 32'd6) <= n_output_len) begin
                                n_lane_count <= 4'd6;
                            end else if ((n_j + 32'd5) <= n_output_len) begin
                                n_lane_count <= 4'd5;
                            end else if ((n_j + 32'd4) <= n_output_len) begin
                                n_lane_count <= 4'd4;
                            end else if ((n_j + 32'd3) <= n_output_len) begin
                                n_lane_count <= 4'd3;
                            end else if ((n_j + 32'd2) <= n_output_len) begin
                                n_lane_count <= 4'd2;
                            end else begin
                                n_lane_count <= 4'd1;
                            end
                        end else if (neural_lane_width_hold == 4'd4) begin
                            if ((n_j + 32'd4) <= n_output_len) begin
                                n_lane_count <= 4'd4;
                            end else if ((n_j + 32'd3) <= n_output_len) begin
                                n_lane_count <= 4'd3;
                            end else if ((n_j + 32'd2) <= n_output_len) begin
                                n_lane_count <= 4'd2;
                            end else begin
                                n_lane_count <= 4'd1;
                            end
                        end else if (neural_lane_width_hold == 4'd2) begin
                            if ((n_j + 32'd2) <= n_output_len) begin
                                n_lane_count <= 4'd2;
                            end else begin
                                n_lane_count <= 4'd1;
                            end
                        end else begin
                            n_lane_count <= 4'd1;
                        end
                        n_lane_idx <= 3'd0;
                        if (SCRATCHPAD_ENABLE && neural_is_v2_hold &&
                            (neural_lane_width_hold == 4'd4 || neural_lane_width_hold == 4'd8)) begin
                            state <= ST_NMATVEC_SCRATCH_INIT;
                        end else begin
                            mem_addr_reg <= n_bias_ptr + (n_j << 2);
                            state <= ST_NMATVEC_LOAD_BIAS;
                        end
                    end
                end

                ST_NMATVEC_SCRATCH_INIT: begin
                    n_scratch_valid <= 1'b1;
                    n_scratch_input_base <= n_input_ptr;
                    n_scratch_weight_row_base <= n_weights_ptr + ((n_j) << 2);
                    n_scratch_prefetch_idx <= 32'd0;
                    n_scratch_prefetch_count <= n_lane_count_u32;
                    n_scratch_refills <= n_scratch_refills + 32'd1;
                    mem_addr_reg <= n_bias_ptr + (n_j << 2);
                    state <= ST_NMATVEC_LOAD_BIAS;
                end

                ST_NMATVEC_SCRATCH_PREFETCH: begin
                    state <= ST_NMATVEC_SCRATCH_READY;
                end

                ST_NMATVEC_SCRATCH_READY: begin
                    mem_addr_reg <= n_bias_ptr + (n_j << 2);
                    state <= ST_NMATVEC_LOAD_BIAS;
                end

                ST_NMATVEC_LOAD_BIAS: begin
                    n_acc_lanes[n_lane_idx] <= mem_rdata;
                    if ((n_lane_idx + 4'd1) < n_lane_count) begin
                        n_lane_idx <= n_lane_idx + 3'd1;
                        mem_addr_reg <= n_bias_ptr + ((n_j + n_lane_idx_u32 + 32'd1) << 2);
                        state <= ST_NMATVEC_LOAD_BIAS_PAIR;
                    end else begin
                        n_i <= 32'd0;
                        state <= ST_NMATVEC_INNER_CHECK;
                    end
                end

                ST_NMATVEC_LOAD_BIAS_PAIR: begin
                    n_acc_lanes[n_lane_idx] <= mem_rdata;
                    if ((n_lane_idx + 4'd1) < n_lane_count) begin
                        n_lane_idx <= n_lane_idx + 3'd1;
                        mem_addr_reg <= n_bias_ptr + ((n_j + n_lane_idx_u32 + 32'd1) << 2);
                        state <= ST_NMATVEC_LOAD_BIAS_PAIR;
                    end else begin
                        n_i <= 32'd0;
                        state <= ST_NMATVEC_INNER_CHECK;
                    end
                end

                ST_NMATVEC_INNER_CHECK: begin
                    if (n_i >= n_input_len) begin
                        n_lane_idx <= 3'd0;
                        mem_addr_reg <= n_output_ptr + (n_j << 2);
                        mem_wdata_reg <= n_acc_lanes[0];
                        mem_size_reg <= 2'b10;
                        mem_we_reg <= 1'b1;
                        if (neural_is_v2_hold) begin
                            state <= ST_NMATVEC_STORE_COMMIT;
                        end else begin
                            state <= ST_NMATVEC_STORE_REQ;
                        end
                    end else begin
                        mem_addr_reg <= n_input_ptr + (n_i << 2);
                        state <= ST_NMATVEC_LOAD_INPUT;
                    end
                end

                ST_NMATVEC_LOAD_INPUT: begin
                    n_tmp_in_bits <= mem_rdata;
                    if (SCRATCHPAD_ENABLE && neural_is_v2_hold &&
                        (neural_lane_width_hold == 4'd4 || neural_lane_width_hold == 4'd8) &&
                        n_lane_count != 4'd0) begin
                        n_scratch_weight_row_base <= n_weights_ptr + (((n_i * n_output_len) + n_j) << 2);
                        n_lane_idx <= 3'd0;
                        mem_addr_reg <= n_weights_ptr + (((n_i * n_output_len) + n_j) << 2);
                        if (neural_parallel_mac4_hold && n_lane_count >= 4'd4) begin
                            mem_addr2_reg <= n_weights_ptr + ((((n_i * n_output_len) + n_j) << 2) + 32'd4);
                            mem_addr3_reg <= n_weights_ptr + ((((n_i * n_output_len) + n_j) << 2) + 32'd8);
                            mem_addr4_reg <= n_weights_ptr + ((((n_i * n_output_len) + n_j) << 2) + 32'd12);
                            state <= ST_NMATVEC_SCRATCH_STREAM_PMAC;
                        end else if (neural_parallel_mac2_hold && n_lane_count >= 4'd3) begin
                            mem_addr2_reg <= n_weights_ptr + ((((n_i * n_output_len) + n_j) << 2) + 32'd4);
                            mem_addr3_reg <= n_weights_ptr + ((((n_i * n_output_len) + n_j) << 2) + 32'd8);
                            mem_addr4_reg <= 32'd0;
                            state <= ST_NMATVEC_SCRATCH_STREAM_PMAC;
                        end else if (neural_parallel_mac_hold && n_lane_count >= 4'd2) begin
                            mem_addr2_reg <= n_weights_ptr + ((((n_i * n_output_len) + n_j) << 2) + 32'd4);
                            mem_addr3_reg <= 32'd0;
                            mem_addr4_reg <= 32'd0;
                            state <= ST_NMATVEC_SCRATCH_STREAM_PMAC;
                        end else begin
                            mem_addr2_reg <= 32'd0;
                            mem_addr3_reg <= 32'd0;
                            mem_addr4_reg <= 32'd0;
                            state <= ST_NMATVEC_SCRATCH_STREAM;
                        end
                    end else begin
                        if (n_scratch_valid) begin
                            n_scratch_hits <= n_scratch_hits + 32'd1;
                        end
                        n_lane_idx <= 3'd0;
                        mem_addr2_reg <= 32'd0;
                        mem_addr3_reg <= 32'd0;
                        mem_addr4_reg <= 32'd0;
                        mem_addr_reg <= n_weights_ptr + (((n_i * n_output_len) + n_j) << 2);
                        state <= ST_NMATVEC_LOAD_WEIGHT;
                    end
                end

                ST_NMATVEC_SCRATCH_STREAM: begin
                    n_scratch_bank[n_lane_idx] <= mem_rdata;
                    n_acc_lanes[n_lane_idx] <= fp_add(n_acc_lanes[n_lane_idx], fp_mul(n_tmp_in_bits, mem_rdata));
                    n_scratch_hits <= n_scratch_hits + 32'd1;
                    if ((n_lane_idx + 4'd1) < n_lane_count) begin
                        n_lane_idx <= n_lane_idx + 3'd1;
                        mem_addr_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd1) << 2);
                        state <= ST_NMATVEC_SCRATCH_STREAM;
                    end else begin
                        n_i <= n_i + 32'd1;
                        state <= ST_NMATVEC_INNER_CHECK;
                    end
                end

                ST_NMATVEC_SCRATCH_STREAM_PMAC: begin
                    n_scratch_bank[n_lane_idx] <= mem_rdata;
                    n_acc_lanes[n_lane_idx] <= fp_add(n_acc_lanes[n_lane_idx], fp_mul(n_tmp_in_bits, mem_rdata));
                    if (neural_parallel_mac4_hold && ((n_lane_idx + 4'd3) < n_lane_count)) begin
                        n_scratch_bank[n_lane_idx + 3'd1] <= mem_rdata2;
                        n_scratch_bank[n_lane_idx + 3'd2] <= mem_rdata3;
                        n_scratch_bank[n_lane_idx + 3'd3] <= mem_rdata4;
                        n_acc_lanes[n_lane_idx + 3'd1] <= fp_add(n_acc_lanes[n_lane_idx + 3'd1], fp_mul(n_tmp_in_bits, mem_rdata2));
                        n_acc_lanes[n_lane_idx + 3'd2] <= fp_add(n_acc_lanes[n_lane_idx + 3'd2], fp_mul(n_tmp_in_bits, mem_rdata3));
                        n_acc_lanes[n_lane_idx + 3'd3] <= fp_add(n_acc_lanes[n_lane_idx + 3'd3], fp_mul(n_tmp_in_bits, mem_rdata4));
                        n_scratch_hits <= n_scratch_hits + 32'd4;
                        if ((n_lane_idx + 4'd4) < n_lane_count) begin
                            n_lane_idx <= n_lane_idx + 3'd4;
                            mem_addr_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd4) << 2);
                            if ((n_lane_idx + 4'd5) < n_lane_count) begin
                                mem_addr2_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd5) << 2);
                            end else begin
                                mem_addr2_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd4) << 2);
                            end
                            if ((n_lane_idx + 4'd6) < n_lane_count) begin
                                mem_addr3_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd6) << 2);
                            end else begin
                                mem_addr3_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd4) << 2);
                            end
                            if ((n_lane_idx + 4'd7) < n_lane_count) begin
                                mem_addr4_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd7) << 2);
                            end else begin
                                mem_addr4_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd4) << 2);
                            end
                            state <= ST_NMATVEC_SCRATCH_STREAM_PMAC;
                        end else begin
                            n_i <= n_i + 32'd1;
                            mem_addr2_reg <= 32'd0;
                            mem_addr3_reg <= 32'd0;
                            mem_addr4_reg <= 32'd0;
                            state <= ST_NMATVEC_INNER_CHECK;
                        end
                    end else if (neural_parallel_mac2_hold && ((n_lane_idx + 4'd2) < n_lane_count)) begin
                        n_scratch_bank[n_lane_idx + 3'd1] <= mem_rdata2;
                        n_scratch_bank[n_lane_idx + 3'd2] <= mem_rdata3;
                        n_acc_lanes[n_lane_idx + 3'd1] <= fp_add(n_acc_lanes[n_lane_idx + 3'd1], fp_mul(n_tmp_in_bits, mem_rdata2));
                        n_acc_lanes[n_lane_idx + 3'd2] <= fp_add(n_acc_lanes[n_lane_idx + 3'd2], fp_mul(n_tmp_in_bits, mem_rdata3));
                        n_scratch_hits <= n_scratch_hits + 32'd3;
                        if ((n_lane_idx + 4'd3) < n_lane_count) begin
                            n_lane_idx <= n_lane_idx + 3'd3;
                            mem_addr_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd3) << 2);
                            if ((n_lane_idx + 4'd4) < n_lane_count) begin
                                mem_addr2_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd4) << 2);
                            end else begin
                                mem_addr2_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd3) << 2);
                            end
                            if ((n_lane_idx + 4'd5) < n_lane_count) begin
                                mem_addr3_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd5) << 2);
                            end else begin
                                mem_addr3_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd3) << 2);
                            end
                            mem_addr4_reg <= 32'd0;
                            state <= ST_NMATVEC_SCRATCH_STREAM_PMAC;
                        end else begin
                            n_i <= n_i + 32'd1;
                            mem_addr2_reg <= 32'd0;
                            mem_addr3_reg <= 32'd0;
                            mem_addr4_reg <= 32'd0;
                            state <= ST_NMATVEC_INNER_CHECK;
                        end
                    end else if ((n_lane_idx + 4'd1) < n_lane_count) begin
                        n_scratch_bank[n_lane_idx + 3'd1] <= mem_rdata2;
                        n_acc_lanes[n_lane_idx + 3'd1] <= fp_add(n_acc_lanes[n_lane_idx + 3'd1], fp_mul(n_tmp_in_bits, mem_rdata2));
                        n_scratch_hits <= n_scratch_hits + 32'd2;
                        if ((n_lane_idx + 4'd2) < n_lane_count) begin
                            n_lane_idx <= n_lane_idx + 3'd2;
                            mem_addr_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd2) << 2);
                            if ((n_lane_idx + 4'd3) < n_lane_count) begin
                                mem_addr2_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd3) << 2);
                            end else begin
                                mem_addr2_reg <= n_scratch_weight_row_base + ((n_lane_idx_u32 + 32'd2) << 2);
                            end
                            mem_addr3_reg <= 32'd0;
                            mem_addr4_reg <= 32'd0;
                            state <= ST_NMATVEC_SCRATCH_STREAM_PMAC;
                        end else begin
                            n_i <= n_i + 32'd1;
                            mem_addr2_reg <= 32'd0;
                            mem_addr3_reg <= 32'd0;
                            mem_addr4_reg <= 32'd0;
                            state <= ST_NMATVEC_INNER_CHECK;
                        end
                    end else begin
                        n_scratch_hits <= n_scratch_hits + 32'd1;
                        n_i <= n_i + 32'd1;
                        mem_addr2_reg <= 32'd0;
                        mem_addr3_reg <= 32'd0;
                        mem_addr4_reg <= 32'd0;
                        state <= ST_NMATVEC_INNER_CHECK;
                    end
                end

                ST_NMATVEC_LOAD_WEIGHT: begin
                    n_tmp_w_bits <= mem_rdata;
                    state <= ST_NMATVEC_MAC;
                end

                ST_NMATVEC_MAC: begin
                    n_acc_lanes[n_lane_idx] <= fp_add(n_acc_lanes[n_lane_idx], fp_mul(n_tmp_in_bits, n_tmp_w_bits));
                    if ((n_lane_idx + 4'd1) < n_lane_count) begin
                        n_lane_idx <= n_lane_idx + 3'd1;
                        mem_addr_reg <= n_weights_ptr + (((n_i * n_output_len) + (n_j + n_lane_idx_u32 + 32'd1)) << 2);
                        state <= ST_NMATVEC_LOAD_WEIGHT_PAIR;
                    end else begin
                        n_i <= n_i + 32'd1;
                        state <= ST_NMATVEC_INNER_CHECK;
                    end
                end

                ST_NMATVEC_LOAD_WEIGHT_PAIR: begin
                    n_tmp_w1_bits <= mem_rdata;
                    state <= ST_NMATVEC_MAC_PAIR;
                end

                ST_NMATVEC_MAC_PAIR: begin
                    n_acc_lanes[n_lane_idx] <= fp_add(n_acc_lanes[n_lane_idx], fp_mul(n_tmp_in_bits, n_tmp_w1_bits));
                    if ((n_lane_idx + 4'd1) < n_lane_count) begin
                        n_lane_idx <= n_lane_idx + 3'd1;
                        mem_addr_reg <= n_weights_ptr + (((n_i * n_output_len) + (n_j + n_lane_idx_u32 + 32'd1)) << 2);
                        state <= ST_NMATVEC_LOAD_WEIGHT_PAIR;
                    end else begin
                        n_i <= n_i + 32'd1;
                        state <= ST_NMATVEC_INNER_CHECK;
                    end
                end

                ST_NMATVEC_STORE_REQ: begin
                    state <= ST_NMATVEC_STORE_COMMIT;
                end

                ST_NMATVEC_STORE_COMMIT: begin
                    if ((n_lane_idx + 4'd1) < n_lane_count) begin
                        n_lane_idx <= n_lane_idx + 3'd1;
                        mem_addr_reg <= n_output_ptr + ((n_j + n_lane_idx_u32 + 32'd1) << 2);
                        mem_wdata_reg <= n_acc_lanes[n_lane_idx + 3'd1];
                        mem_size_reg <= 2'b10;
                        mem_we_reg <= 1'b1;
                        if (neural_is_v2_hold) begin
                            state <= ST_NMATVEC_STORE2_COMMIT;
                        end else begin
                            state <= ST_NMATVEC_STORE2_REQ;
                        end
                    end else begin
                        n_j <= n_j + n_lane_count_u32;
                        state <= ST_NMATVEC_OUTER_CHECK;
                    end
                end

                ST_NMATVEC_STORE2_REQ: begin
                    state <= ST_NMATVEC_STORE2_COMMIT;
                end

                ST_NMATVEC_STORE2_COMMIT: begin
                    state <= ST_NMATVEC_STORE_COMMIT;
                end

                ST_NVEC_VALIDATE: begin
                    if (!(neural_op_hold == 5'd1 || neural_op_hold == 5'd2 || neural_op_hold == 5'd3)) begin
                        // Fail loud on unsupported neural opcode (matches C++ throw path).
                        halted <= 1'b1;
                        exit_code <= 32'd1;
                    end else if (n_len == 32'd0) begin
                        neural_status <= NEURAL_ERR_INVALID_LEN;
                        state <= ST_NEURAL_FINISH;
                    end else if ((neural_op_hold == 5'd1 || neural_op_hold == 5'd2) &&
                                 (n_dst_ptr[1:0] != 2'b00 || n_src_ptr[1:0] != 2'b00)) begin
                        neural_status <= NEURAL_ERR_UNALIGNED;
                        state <= ST_NEURAL_FINISH;
                    end else if ((neural_op_hold == 5'd3) && (n_src_ptr[1:0] != 2'b00)) begin
                        neural_status <= NEURAL_ERR_UNALIGNED;
                        state <= ST_NEURAL_FINISH;
                    end else if ((neural_op_hold == 5'd1 || neural_op_hold == 5'd2) &&
                                 ((n_dst_ptr + (n_len << 2)) > MEM_SIZE || (n_src_ptr + (n_len << 2)) > MEM_SIZE)) begin
                        neural_status <= NEURAL_ERR_INVALID_PTR;
                        state <= ST_NEURAL_FINISH;
                    end else if ((neural_op_hold == 5'd3) &&
                                 ((n_dst_ptr + n_len) > MEM_SIZE || (n_src_ptr + (n_len << 2)) > MEM_SIZE)) begin
                        neural_status <= NEURAL_ERR_INVALID_PTR;
                        state <= ST_NEURAL_FINISH;
                    end else begin
                        n_idx <= 32'd0;
                        state <= ST_NVEC_LOOP_CHECK;
                    end
                end

                ST_NVEC_LOOP_CHECK: begin
                    if (n_idx >= n_len) begin
                        neural_status <= NEURAL_ERR_OK;
                        state <= ST_NEURAL_FINISH;
                    end else begin
                        mem_addr_reg <= n_src_ptr + (n_idx << 2);
                        state <= ST_NVEC_LOAD_SRC;
                    end
                end

                ST_NVEC_LOAD_SRC: begin
                    n_src_bits <= mem_rdata;
                    state <= ST_NVEC_COMPUTE;
                end

                ST_NVEC_COMPUTE: begin
                    if (neural_op_hold == 5'd1) begin
                        // ReLU: y = max(x, 0), NaN -> 0 (matches C++ x>0 ? x : 0)
                        if ((n_src_bits[30:23] == 8'hFF && n_src_bits[22:0] != 23'd0) ||
                            n_src_bits[31] ||
                            (n_src_bits[30:0] == 31'd0)) begin
                            n_dst_bits <= F32_ZERO;
                            mem_wdata_reg <= F32_ZERO;
                        end else begin
                            n_dst_bits <= n_src_bits;
                            mem_wdata_reg <= n_src_bits;
                        end
                        mem_addr_reg <= n_dst_ptr + (n_idx << 2);
                        mem_size_reg <= 2'b10;
                        mem_we_reg <= 1'b1;
                        if (neural_is_v2_hold) begin
                            state <= ST_NVEC_STORE_COMMIT;
                        end else begin
                            state <= ST_NVEC_STORE_REQ;
                        end
                    end else if (neural_op_hold == 5'd2) begin
                        // Sigmoid PWL:
                        // x <= -4 => 0, x >= 4 => 1, else 0.5 + x*0.125
                        if (fp_cmp_le(n_src_bits, F32_NEG4)) begin
                            n_dst_bits <= F32_ZERO;
                            mem_wdata_reg <= F32_ZERO;
                        end else if (fp_cmp_le(F32_POS4, n_src_bits)) begin
                            n_dst_bits <= F32_ONE;
                            mem_wdata_reg <= F32_ONE;
                        end else begin
                            n_dst_bits <= fp_add(F32_HALF, fp_mul(n_src_bits, F32_1_8));
                            mem_wdata_reg <= fp_add(F32_HALF, fp_mul(n_src_bits, F32_1_8));
                        end
                        mem_addr_reg <= n_dst_ptr + (n_idx << 2);
                        mem_size_reg <= 2'b10;
                        mem_we_reg <= 1'b1;
                        if (neural_is_v2_hold) begin
                            state <= ST_NVEC_STORE_COMMIT;
                        end else begin
                            state <= ST_NVEC_STORE_REQ;
                        end
                    end else begin
                        // Clamp+scale to u8, NaN -> 0
                        if (n_src_bits[30:23] == 8'hFF && n_src_bits[22:0] != 23'd0) begin
                            n_dst_bits <= 32'd0;
                            mem_wdata_reg <= 32'd0;
                        end else if (fp_cmp_lt(n_src_bits, F32_ZERO)) begin
                            n_dst_bits <= 32'd0;
                            mem_wdata_reg <= 32'd0;
                        end else if (fp_cmp_lt(F32_ONE, n_src_bits)) begin
                            n_dst_bits <= 32'd255;
                            mem_wdata_reg <= 32'd255;
                        end else begin
                            n_dst_bits <= fp_cvt_w_s(fp_mul(n_src_bits, F32_255));
                            mem_wdata_reg <= fp_cvt_w_s(fp_mul(n_src_bits, F32_255));
                        end
                        mem_addr_reg <= n_dst_ptr + n_idx;
                        mem_size_reg <= 2'b00;
                        mem_we_reg <= 1'b1;
                        if (neural_is_v2_hold) begin
                            state <= ST_NVEC_STORE_COMMIT;
                        end else begin
                            state <= ST_NVEC_STORE_REQ;
                        end
                    end
                end

                ST_NVEC_STORE_REQ: begin
                    state <= ST_NVEC_STORE_COMMIT;
                end

                ST_NVEC_STORE_COMMIT: begin
                    n_idx <= n_idx + 32'd1;
                    state <= ST_NVEC_LOOP_CHECK;
                end

                ST_NEURAL_FINISH: begin
                    if (neural_rd_hold != 5'd0) begin
                        regs[neural_rd_hold] <= neural_status;
                    end
                    pc <= pc + 4;
                    state <= ST_EXEC;
                end
            endcase
        end
    end

endmodule

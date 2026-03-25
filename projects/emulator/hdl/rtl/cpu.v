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
    output wire [31:0] mem_wdata,
    input  wire [31:0] mem_rdata,
    output wire        mem_we,
    output wire [1:0]  mem_size,
    
    // Register initialization (external write)
    input  wire        reg_write_en,
    input  wire [4:0]  reg_write_addr,
    input  wire [31:0] reg_write_data,
    input  wire        force_a0_en,
    input  wire [31:0] force_a0_data,
    
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
    output reg  [31:0] exit_code
);

    // Opcodes (RISC-V encoding)
    localparam OP_LOAD     = 7'b0000011;
    localparam OP_LOAD_FP  = 7'b0000111;
    localparam OP_OP_IMM   = 7'b0010011;
    localparam OP_AUIPC    = 7'b0010111;
    localparam OP_STORE    = 7'b0100011;
    localparam OP_STORE_FP = 7'b0100111;
    localparam OP_OP       = 7'b0110011;
    localparam OP_OP_FP    = 7'b1010011;
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
    reg [1:0] state;
    localparam ST_EXEC     = 2'd0;
    localparam ST_SYSCALL  = 2'd1;
    localparam ST_LOAD     = 2'd2;
    localparam ST_LOAD_FP  = 2'd3;
    wire load_pending = (state == ST_LOAD) || (state == ST_LOAD_FP);
    
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
            mem_wdata_reg <= 32'd0;
            mem_size_reg <= 2'b10;
            load_rd <= 5'd0;
            load_funct3 <= 3'd0;
            
            // Reset registers
            for (i = 0; i < 32; i = i + 1) begin
                regs[i] <= 32'd0;
                fp_regs[i] <= 32'd0;
            end
            
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
            endcase
        end
    end

endmodule

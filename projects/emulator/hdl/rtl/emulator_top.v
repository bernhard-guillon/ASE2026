// RISC-V RV32IF Emulator - Top Level Module
// Synthesizable design for simulation with Verilator

module emulator_top #(
    parameter MEM_SIZE = 32'h800000,  // 8MB default for simulation
    parameter FRAMEBUFFER_ADDR = 32'h20000,
    parameter FRAMEBUFFER_SIZE = 400    // 20x20 pixels
)(
    input  wire        clk,
    input  wire        rst_n,
    
    // Control interface
    input  wire        start,
    output wire        halted,
    output wire [31:0] exit_code,
    output wire [31:0] cycle_count,
    
    // Register initialization (for setting a0 with char code)
    input  wire        reg_write_en,
    input  wire [4:0]  reg_write_addr,
    input  wire [31:0] reg_write_data,
    input  wire        force_a0_en,
    input  wire [31:0] force_a0_data,
    
    // Memory initialization interface
    input  wire        mem_init_en,
    input  wire [31:0] mem_init_addr,
    input  wire [7:0]  mem_init_data,
    
    // Memory read interface (for framebuffer extraction)
    input  wire [31:0] mem_read_addr,
    output wire [7:0]  mem_read_data,
    
    // PC initialization (for ELF entry point)
    input  wire        pc_init_en,
    input  wire [31:0] pc_init_addr,

    // Pause (gates CPU enable so testbench can write memory without CPU advancing)
    input  wire        pause,

    // Syscall interface (directly wire to testbench)
    output wire [31:0] debug_pc,
    output wire        syscall_valid,
    output wire [31:0] syscall_num,
    output wire [31:0] syscall_a0,
    output wire [31:0] syscall_a1,
    output wire [31:0] syscall_a2,
    output wire [31:0] syscall_a3,
    output wire [31:0] syscall_a4,
    output wire [31:0] syscall_a5,
    input  wire        syscall_done,
    input  wire [31:0] syscall_ret,

    // Debug ports
    output wire [31:0] debug_ra,
    output wire [31:0] debug_sp
);

    // Internal signals
    wire [31:0] pc;
    wire [31:0] instruction;
    wire [31:0] mem_addr;
    wire [31:0] mem_addr2;
    wire [31:0] mem_addr3;
    wire [31:0] mem_addr4;
    wire [31:0] mem_wdata;
    wire [31:0] mem_rdata;
    wire [31:0] mem_rdata2;
    wire [31:0] mem_rdata3;
    wire [31:0] mem_rdata4;
    wire        mem_we;
    wire [1:0]  mem_size;  // 00=byte, 01=half, 10=word
    
    // CPU state
    reg         running;
    reg [31:0]  cycles;
    reg         cpu_halted;
    reg [31:0]  cpu_exit_code;
    
    // Instantiate CPU
    cpu cpu_inst (
        .clk(clk),
        .rst_n(rst_n),
        .enable(running && !cpu_halted && !pause),
        
        // Instruction fetch
        .pc(pc),
        .instruction(instruction),
        
        // Data memory interface
        .mem_addr(mem_addr),
        .mem_addr2(mem_addr2),
        .mem_addr3(mem_addr3),
        .mem_addr4(mem_addr4),
        .mem_wdata(mem_wdata),
        .mem_rdata(mem_rdata),
        .mem_rdata2(mem_rdata2),
        .mem_rdata3(mem_rdata3),
        .mem_rdata4(mem_rdata4),
        .mem_we(mem_we),
        .mem_size(mem_size),
        
        // Register initialization
        .pc_init_en(pc_init_en && !running),
        .pc_init_addr(pc_init_addr),
        .reg_write_en(reg_write_en && !running),
        .reg_write_addr(reg_write_addr),
        .reg_write_data(reg_write_data),
        .force_a0_en(force_a0_en),
        .force_a0_data(force_a0_data),
        
        // Syscall interface
        .syscall_valid(syscall_valid),
        .syscall_num(syscall_num),
        .syscall_a0(syscall_a0),
        .syscall_a1(syscall_a1),
        .syscall_a2(syscall_a2),
        .syscall_a3(syscall_a3),
        .syscall_a4(syscall_a4),
        .syscall_a5(syscall_a5),
        .syscall_done(syscall_done),
        .syscall_ret(syscall_ret),
        
        // Halt signal
        .halted(cpu_halted),
        .exit_code(cpu_exit_code),
        
        // Debug ports
        .debug_ra(debug_ra),
        .debug_sp(debug_sp)
    );
    
    // Instantiate Memory
    memory #(
        .SIZE(MEM_SIZE)
    ) mem_inst (
        .clk(clk),
        
        // Instruction fetch port (read-only)
        .i_addr(pc),
        .i_data(instruction),
        
        // Data port (read/write)
        .d_addr(mem_addr),
        .d_addr2(mem_addr2),
        .d_addr3(mem_addr3),
        .d_addr4(mem_addr4),
        .d_wdata(mem_wdata),
        .d_rdata(mem_rdata),
        .d_rdata2(mem_rdata2),
        .d_rdata3(mem_rdata3),
        .d_rdata4(mem_rdata4),
        .d_we(mem_we && running),
        .d_size(mem_size),
        
        // Initialization port
        .init_en(mem_init_en),
        .init_addr(mem_init_addr),
        .init_data(mem_init_data),
        
        // Read port for testbench
        .tb_addr(mem_read_addr),
        .tb_data(mem_read_data)
    );
    
    // Control logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running <= 1'b0;
            cycles <= 32'd0;
        end else begin
            if (start && !running) begin
                running <= 1'b1;
                cycles <= 32'd0;
            end else if (running && !cpu_halted) begin
                cycles <= cycles + 1;
            end
        end
    end
    
    // Output assignments
    assign halted = cpu_halted;
    assign exit_code = cpu_exit_code;
    assign cycle_count = cycles;
    assign debug_pc = pc;

endmodule

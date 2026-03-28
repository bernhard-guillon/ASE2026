// Memory Module for RISC-V Emulator
// Dual-port: instruction fetch + data access
// Little-endian byte ordering

module memory #(
    parameter SIZE = 32'h200000  // 2MB default for simulation (configurable)
)(
    input  wire        clk,
    
    // Instruction fetch port (read-only)
    input  wire [31:0] i_addr,
    output wire [31:0] i_data,
    
    // Data port (read/write)
    input  wire [31:0] d_addr,
    input  wire [31:0] d_addr2,
    input  wire [31:0] d_addr3,
    input  wire [31:0] d_wdata,
    output wire [31:0] d_rdata,
    output wire [31:0] d_rdata2,
    output wire [31:0] d_rdata3,
    input  wire        d_we,
    input  wire [1:0]  d_size,  // 00=byte, 01=half, 10=word
    
    // Initialization port (for loading ELF)
    input  wire        init_en,
    input  wire [31:0] init_addr,
    input  wire [7:0]  init_data,
    
    // Testbench read port (for framebuffer extraction)
    input  wire [31:0] tb_addr,
    output wire [7:0]  tb_data
);

    // Memory array - Verilator uses sparse representation for large arrays
    reg [7:0] mem [0:SIZE-1];
    
    // Instruction fetch (word-aligned read)
    assign i_data = {mem[i_addr+3], mem[i_addr+2], mem[i_addr+1], mem[i_addr]};
    
    // Data read (little-endian)
    wire [31:0] d_word = {mem[d_addr+3], mem[d_addr+2], mem[d_addr+1], mem[d_addr]};
    wire [31:0] d_word2 = {mem[d_addr2+3], mem[d_addr2+2], mem[d_addr2+1], mem[d_addr2]};
    wire [31:0] d_word3 = {mem[d_addr3+3], mem[d_addr3+2], mem[d_addr3+1], mem[d_addr3]};
    assign d_rdata = d_word;
    assign d_rdata2 = d_word2;
    assign d_rdata3 = d_word3;
    
    // Testbench read
    assign tb_data = mem[tb_addr];
    
    // Write logic
    always @(posedge clk) begin
        if (init_en) begin
            // Initialization write (byte)
            mem[init_addr] <= init_data;
        end else if (d_we) begin
            // Data write
            case (d_size)
                2'b00: begin  // Byte
                    mem[d_addr] <= d_wdata[7:0];
                end
                2'b01: begin  // Halfword
                    mem[d_addr]   <= d_wdata[7:0];
                    mem[d_addr+1] <= d_wdata[15:8];
                end
                2'b10: begin  // Word
                    mem[d_addr]   <= d_wdata[7:0];
                    mem[d_addr+1] <= d_wdata[15:8];
                    mem[d_addr+2] <= d_wdata[23:16];
                    mem[d_addr+3] <= d_wdata[31:24];
                end
                default: begin
                    mem[d_addr]   <= d_wdata[7:0];
                    mem[d_addr+1] <= d_wdata[15:8];
                    mem[d_addr+2] <= d_wdata[23:16];
                    mem[d_addr+3] <= d_wdata[31:24];
                end
            endcase
        end
    end

endmodule

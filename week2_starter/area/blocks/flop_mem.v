// Flop-based memory: one write port (from the loader), NREAD read ports.
// Models a rule/instruction store built from flip-flops.
`default_nettype none
module flop_mem #(
    parameter ADDR_W = 5,          // 2**ADDR_W entries
    parameter DATA_W = 128,        // bits per entry
    parameter NREAD  = 1           // read ports (one per lane)
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     we,
    input  wire [ADDR_W-1:0]        waddr,
    input  wire [DATA_W-1:0]        wdata,
    input  wire [NREAD*ADDR_W-1:0]  raddr,
    output wire [NREAD*DATA_W-1:0]  rdata
);
    reg [DATA_W-1:0] mem [0:(1<<ADDR_W)-1];
    integer i;
    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < (1<<ADDR_W); i = i + 1) mem[i] <= {DATA_W{1'b0}};
        end else if (we) begin
            mem[waddr] <= wdata;
        end
    end
    genvar r;
    generate for (r = 0; r < NREAD; r = r + 1) begin : g_rd
        assign rdata[r*DATA_W +: DATA_W] = mem[raddr[r*ADDR_W +: ADDR_W]];
    end endgenerate
endmodule

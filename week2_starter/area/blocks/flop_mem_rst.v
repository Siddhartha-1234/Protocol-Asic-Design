/* verilator lint_off UNUSEDSIGNAL */  // rst_n and i are unused in some RST variants
// Same memory, three reset styles: RST=0 none, RST=1 synchronous, RST=2 asynchronous.
`default_nettype none
module flop_mem_rst #(parameter ADDR_W = 5, parameter DATA_W = 128, parameter RST = 0) (
    input  wire              clk, rst_n, we,
    input  wire [ADDR_W-1:0] waddr, raddr,
    input  wire [DATA_W-1:0] wdata,
    output wire [DATA_W-1:0] rdata
);
    reg [DATA_W-1:0] mem [0:(1<<ADDR_W)-1];
    integer i;
    generate
    if (RST == 2) begin : g_async
        always @(posedge clk or negedge rst_n)
            if (!rst_n) for (i = 0; i < (1<<ADDR_W); i = i + 1) mem[i] <= 0;
            else if (we) mem[waddr] <= wdata;
    end else if (RST == 1) begin : g_sync
        always @(posedge clk)
            if (!rst_n) for (i = 0; i < (1<<ADDR_W); i = i + 1) mem[i] <= 0;
            else if (we) mem[waddr] <= wdata;
    end else begin : g_none
        always @(posedge clk)
            if (we) mem[waddr] <= wdata;
    end
    endgenerate
    assign rdata = mem[raddr];
endmodule

// 6-bit bit counter: load, decrement, zero flag.
`default_nettype none
module counter6 (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       load,
    input  wire       dec,
    input  wire [5:0] init,
    output wire       zero
);
    reg [5:0] c;
    always @(posedge clk) begin
        if (!rst_n)              c <= 6'd0;
        else if (load)           c <= init;
        else if (dec && c != 0)  c <= c - 6'd1;
    end
    assign zero = (c == 6'd0);
endmodule

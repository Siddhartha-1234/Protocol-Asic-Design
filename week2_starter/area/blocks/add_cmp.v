// Timing experiment: a W-bit add feeding a compare, registered at both ends.
// PIPE=1 inserts a register between the adder and the compare.
`default_nettype none
module add_cmp #(parameter W = 32, parameter PIPE = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire [W-1:0] c,
    output reg          hit
);
    reg [W-1:0] ra, rb, rc, rc2;
    reg [W-1:0] sum_q;
    wire [W-1:0] sum = ra + rb;    // carry-out dropped: keeps the example simple
    always @(posedge clk) begin
        if (!rst_n) begin ra <= 0; rb <= 0; rc <= 0; rc2 <= 0; sum_q <= 0; hit <= 0; end
        else begin
            ra <= a; rb <= b; rc <= c;
            sum_q <= sum; rc2 <= rc;
            hit <= PIPE ? (sum_q > rc2) : (sum > rc);
        end
    end
endmodule

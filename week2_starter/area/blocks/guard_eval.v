// 4 guards, each picks 2 of NSRC sources (with polarity), ANDs them;
// a priority encoder picks the first true rule.
`default_nettype none
module guard_eval #(parameter NSRC = 32, parameter SEL_W = 5) (
    input  wire [NSRC-1:0]    src,
    input  wire [4*2*SEL_W-1:0] sel,   // 4 rules x 2 guards x select
    input  wire [4*2-1:0]     pol,     // polarity per guard
    output reg  [1:0]         winner,
    output reg                any
);
    wire [3:0] hit;
    genvar r;
    generate for (r = 0; r < 4; r = r + 1) begin : g_r
        wire a = src[sel[(2*r)*SEL_W +: SEL_W]]   ^ pol[2*r];
        wire b = src[sel[(2*r+1)*SEL_W +: SEL_W]] ^ pol[2*r+1];
        assign hit[r] = a & b;
    end endgenerate
    always @* begin
        any = |hit;
        casez (hit)
            4'b???1: winner = 2'd0;
            4'b??10: winner = 2'd1;
            4'b?100: winner = 2'd2;
            default: winner = 2'd3;
        endcase
    end
endmodule

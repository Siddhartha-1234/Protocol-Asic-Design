// 2-flop synchroniser + edge detector on N pins.
`default_nettype none
module pin_sync #(parameter N = 16) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [N-1:0] pins,
    output wire [N-1:0] level,
    output wire [N-1:0] rise,
    output wire [N-1:0] fall
);
    reg [N-1:0] s1, s2, s3;
    always @(posedge clk) begin
        if (!rst_n) begin s1 <= 0; s2 <= 0; s3 <= 0; end
        else begin s1 <= pins; s2 <= s1; s3 <= s2; end
    end
    assign level = s2;
    assign rise  =  s2 & ~s3;
    assign fall  = ~s2 &  s3;
endmodule

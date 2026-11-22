// 16-bit down-timer with two reload values and a zero flag.
`default_nettype none
module timer16 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        load_a,
    input  wire        load_b,
    input  wire [15:0] reload_a,
    input  wire [15:0] reload_b,
    output wire        zero
);
    reg [15:0] cnt;
    always @(posedge clk) begin
        if (!rst_n)       cnt <= 16'd0;
        else if (load_a)  cnt <= reload_a;
        else if (load_b)  cnt <= reload_b;
        else if (cnt != 0) cnt <= cnt - 16'd1;
    end
    assign zero = (cnt == 16'd0);
endmodule

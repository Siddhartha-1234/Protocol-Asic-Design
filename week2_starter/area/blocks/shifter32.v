// 32-bit shift register: parallel load, shift left (MSB first) or right (LSB first).
`default_nettype none
module shifter32 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        load,
    input  wire [31:0] din,
    input  wire        shift,
    input  wire        msb_first,
    input  wire        sin,
    output wire        sout,
    output wire [31:0] q
);
    reg [31:0] sr;
    always @(posedge clk) begin
        if (!rst_n)      sr <= 32'd0;
        else if (load)   sr <= din;
        else if (shift)  sr <= msb_first ? {sr[30:0], sin} : {sin, sr[31:1]};
    end
    assign sout = msb_first ? sr[31] : sr[0];
    assign q = sr;
endmodule

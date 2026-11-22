/*
 * Timing lab: a W-bit add feeding a compare, between registers.
 * ui_in is shifted into registers a, b, c (8 bits per clock), so every
 * path of interest is register-to-register. Output: uo_out[0] = (a + b > c).
 * Change PIPE to 1 to add a pipeline register between the add and the compare.
 */
`default_nettype none

module tt_um_timing_lab #(
    parameter W    = 32,
    parameter PIPE = 0
) (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
    reg [3*W-1:0] load_sr;
    always @(posedge clk) begin
        if (!rst_n) load_sr <= {3*W{1'b0}};
        else        load_sr <= {load_sr[3*W-9:0], ui_in};
    end

    wire hit;
    add_cmp #(.W(W), .PIPE(PIPE)) core (
        .clk(clk), .rst_n(rst_n),
        .a(load_sr[W-1:0]), .b(load_sr[2*W-1:W]), .c(load_sr[3*W-1:2*W]),
        .hit(hit)
    );

    assign uo_out  = {7'b0, hit};
    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;
    wire _unused = &{ena, uio_in, 1'b0};
endmodule

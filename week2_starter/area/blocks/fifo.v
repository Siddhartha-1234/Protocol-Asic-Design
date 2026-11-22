// Small synchronous FIFO built from flops (one per lane per direction).
`default_nettype none
module fifo #(parameter W = 8, parameter DEPTH_LOG2 = 2) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] din,
    input  wire         pop,
    output wire [W-1:0] dout,
    output wire         empty,
    output wire         full
);
    localparam D = 1 << DEPTH_LOG2;
    reg [W-1:0]          mem [0:D-1];
    reg [DEPTH_LOG2:0]   wp, rp;       // one extra bit tells full from empty
    always @(posedge clk) begin
        if (!rst_n) begin
            wp <= 0;
            rp <= 0;
        end else begin
            if (push && !full) begin
                mem[wp[DEPTH_LOG2-1:0]] <= din;
                wp <= wp + 1'b1;
            end
            if (pop && !empty) rp <= rp + 1'b1;
        end
    end
    assign dout  = mem[rp[DEPTH_LOG2-1:0]];
    assign empty = (wp == rp);
    assign full  = (wp[DEPTH_LOG2-1:0] == rp[DEPTH_LOG2-1:0]) && (wp[DEPTH_LOG2] != rp[DEPTH_LOG2]);
endmodule

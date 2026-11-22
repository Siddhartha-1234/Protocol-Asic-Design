/*
 * Week-2 STAND-IN design so the test infrastructure has something to test.
 * Replace it with your own Week-1 UART TX (or, from Week 3, the engine).
 *   ui_in[7:0]  byte to send
 *   uio[0]      SEND (input): a rising edge starts a frame
 *   uo_out[0]   TX line, 8N1, LSB first
 *   uo_out[1]   BUSY
 *   uio[1]      ACT (open-drain output): pulled low while busy, released when idle
 *   uio[2]      ECHO_IN (input), copied to uo_out[2] after a 2-flop synchroniser
 */
`default_nettype none

module tt_um_w2_standin #(
    parameter CLKS_PER_BIT = 434          // 50 MHz / 115200 baud
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
    // 2-flop synchronisers on the asynchronous inputs we sample
    reg [2:0] send_s;        // [0],[1] = synchroniser, [2] = previous value for edge detect
    reg [1:0] echo_s;
    always @(posedge clk) begin
        if (!rst_n) begin
            send_s <= 3'b000;
            echo_s <= 2'b00;
        end else begin
            send_s <= {send_s[1:0], uio_in[0]};
            echo_s <= {echo_s[0], uio_in[2]};
        end
    end
    wire send_rise = send_s[1] & ~send_s[2];

    reg [9:0]  frame;        // {stop, data[7:0], start}, shifted out LSB first
    reg [3:0]  bits_left;
    reg [15:0] tick;         // cycles left in the current bit
    reg        tx;
    wire busy = (bits_left != 4'd0) || (tick != 16'd0);

    always @(posedge clk) begin
        if (!rst_n) begin
            frame     <= 10'h3FF;
            bits_left <= 4'd0;
            tick      <= 16'd0;
            tx        <= 1'b1;
        end else if (tick != 16'd0) begin
            tick <= tick - 16'd1;
        end else if (bits_left != 4'd0) begin
            tx        <= frame[0];
            frame     <= {1'b1, frame[9:1]};
            bits_left <= bits_left - 4'd1;
            tick      <= CLKS_PER_BIT - 1;
        end else if (send_rise) begin
            frame     <= {1'b1, ui_in, 1'b0};
            bits_left <= 4'd10;
        end
    end

    reg busy_q;              // registered so the output pin is glitch-free
    always @(posedge clk) begin
        if (!rst_n) busy_q <= 1'b0;
        else        busy_q <= busy | send_rise;
    end

    assign uo_out  = {5'b0, echo_s[1], busy_q, tx};
    assign uio_out = 8'b0;                   // open-drain: we only ever drive 0
    assign uio_oe  = {6'b0, busy_q, 1'b0};   // uio[1] driven low while busy

    wire _unused = &{ena, uio_in[7:3], uio_in[1], 1'b0};
endmodule

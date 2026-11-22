/*
 * Copyright (c) 2026 Siddhartha
 * SPDX-License-Identifier: Apache-2.0
 *
 * 8N1 UART transmitter core: 1 start bit (0), 8 data bits LSB first, 1 stop bit (1).
 */

`default_nettype none

module uart_tx #(
    parameter [8:0] CLKS_PER_BIT_SLOW = 9'd434,  // 50 MHz / 115200 = 434.03
    parameter [8:0] CLKS_PER_BIT_FAST = 9'd50    // 50 MHz / 1 000 000 = 50
) (
    input  wire       clk,
    input  wire       rst_n,     // synchronous, active low
    input  wire [7:0] data,      // byte to send, sampled on the rising edge of send
    input  wire       send,      // already synchronised; rising edge starts a frame
    input  wire       fast,      // already synchronised; 1 = fast baud rate
    output wire       tx,        // serial line, idles high
    output reg        busy       // high while a frame is on the line
);

  localparam [8:0] SLOW_LAST = CLKS_PER_BIT_SLOW - 9'd1;
  localparam [8:0] FAST_LAST = CLKS_PER_BIT_FAST - 9'd1;

  // Rising-edge detector on the (already synchronised) send input.
  reg  send_prev;
  wire send_rise = send & ~send_prev;

  // The shift register holds {stop, data[7:0], start} and shifts right,
  // filling with 1s. Bit 0 IS the TX line, so TX comes straight from a
  // flop (no glitches) and reads 1 (idle) whenever nothing is being sent.
  reg [9:0] shifter;
  reg [3:0] bit_idx;    // which of the 10 bits is on the line (0..9)
  reg [8:0] baud_cnt;   // clock cycles spent on the current bit so far
  reg [8:0] baud_last;  // bit period - 1, latched at the start of a frame

  always @(posedge clk) begin
    if (!rst_n) begin
      send_prev <= 1'b0;
      busy      <= 1'b0;
      shifter   <= 10'h3FF;  // line idles high straight out of reset
      bit_idx   <= 4'd0;
      baud_cnt  <= 9'd0;
      baud_last <= SLOW_LAST;
    end else begin
      send_prev <= send;
      if (!busy) begin
        if (send_rise) begin
          busy      <= 1'b1;
          shifter   <= {1'b1, data, 1'b0};  // stop, data, start
          bit_idx   <= 4'd0;
          baud_cnt  <= 9'd0;
          baud_last <= fast ? FAST_LAST : SLOW_LAST;
        end
      end else if (baud_cnt == baud_last) begin
        baud_cnt <= 9'd0;
        shifter  <= {1'b1, shifter[9:1]};
        if (bit_idx == 4'd9) busy <= 1'b0;  // stop bit has finished
        else bit_idx <= bit_idx + 4'd1;
      end else begin
        baud_cnt <= baud_cnt + 9'd1;
      end
    end
  end

  assign tx = shifter[0];

endmodule

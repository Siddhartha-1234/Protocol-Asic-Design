/*
 * Copyright (c) 2026 Siddhartha
 * SPDX-License-Identifier: Apache-2.0
 *
 * Tiny Tapeout top level for the Week 1 UART transmitter.
 *   ui_in[7:0] : DATA  byte to send (hold stable until BUSY goes high)
 *   uio_in[0]  : SEND  rising edge starts one frame
 *   uio_in[1]  : BAUD  0 = 115200 baud, 1 = 1 Mbaud (with a 50 MHz clock)
 *   uo_out[0]  : TX    serial output, idles high
 *   uo_out[1]  : BUSY  high while a frame is being sent
 */

`default_nettype none

module tt_um_novapranay_uart_tx (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // Pins are asynchronous to clk: pass each control input through two flops.
  reg [1:0] send_sync;
  reg [1:0] baud_sync;

  always @(posedge clk) begin
    if (!rst_n) begin
      send_sync <= 2'b00;
      baud_sync <= 2'b00;
    end else begin
      send_sync <= {send_sync[0], uio_in[0]};
      baud_sync <= {baud_sync[0], uio_in[1]};
    end
  end

  wire tx;
  wire busy;

  uart_tx u_tx (
      .clk  (clk),
      .rst_n(rst_n),
      .data (ui_in),         // not synchronised: SEND qualifies it (see guide)
      .send (send_sync[1]),
      .fast (baud_sync[1]),
      .tx   (tx),
      .busy (busy)
  );

  // Every output must be driven.
  assign uo_out  = {6'b000000, busy, tx};
  assign uio_out = 8'h00;
  assign uio_oe  = 8'h00;  // all bidirectional pins are used as inputs

  // Tell the linter these inputs are unused on purpose.
  wire _unused = &{ena, uio_in[7:2], 1'b0};

endmodule

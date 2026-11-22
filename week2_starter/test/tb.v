`default_nettype none
`timescale 1ns / 1ps

/* Testbench wrapper. Compared with the template it adds a model of the world
   outside the chip on the 8 bidirectional pins, so open-drain protocols (I2C)
   and bus fights can be tested:
     ext_oe/ext_out : a push-pull device outside the chip drives the pin
     ext_pull_low   : an open-drain device outside the chip pulls the pin low
     pull_up         : an external pull-up resistor sits on the pin (I2C Pmod)
   uio_bus is what the wire actually carries; the chip's uio_in sees it.
   contention goes high if two drivers fight (one drives 0, another 1).
*/
module tb ();

  initial begin
    $dumpfile("tb.fst");
    $dumpvars(0, tb);
    #1;
  end

  reg clk;
  reg rst_n;
  reg ena;
  reg  [7:0] ui_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  reg  [7:0] ext_oe;
  reg  [7:0] ext_out;
  reg  [7:0] ext_pull_low;
  reg  [7:0] pull_up;

  wire [7:0] drv0 = (uio_oe & ~uio_out) | (ext_oe & ~ext_out) | ext_pull_low;
  wire [7:0] drv1 = (uio_oe &  uio_out) | (ext_oe &  ext_out);
  wire [7:0] uio_bus;
  wire [7:0] uio_in = uio_bus;
  wire       contention = |(drv0 & drv1);

  genvar i;
  generate
    for (i = 0; i < 8; i = i + 1) begin : g_bus
      assign uio_bus[i] = (drv0[i] & drv1[i]) ? 1'bx :
                          drv0[i]             ? 1'b0 :
                          drv1[i]             ? 1'b1 :
                          pull_up[i]           ? 1'b1 : 1'bz;
    end
  endgenerate

`ifdef GL_TEST
  // Gate-level netlist: parameters are already baked in.
  tt_um_w2_standin user_project (
`else
  tt_um_w2_standin #(.CLKS_PER_BIT(`CLKS_PER_BIT)) user_project (
`endif
      .ui_in  (ui_in),
      .uo_out (uo_out),
      .uio_in (uio_in),
      .uio_out(uio_out),
      .uio_oe (uio_oe),
      .ena    (ena),
      .clk    (clk),
      .rst_n  (rst_n)
  );

endmodule

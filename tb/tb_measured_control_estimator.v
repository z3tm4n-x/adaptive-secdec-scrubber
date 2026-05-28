`timescale 1ns/1ps

module tb_measured_control_estimator;

localparam WINDOW_CYCLES = 4;

reg clk;
reg rst;
reg enable;

reg [31:0] corrected_error_count;
reg [31:0] uncorrectable_error_count;

wire [2:0] measured_ctrl_level;
wire       measured_ctrl_valid;
wire       measured_ctrl_update;
wire [31:0] measured_window_count;
wire [31:0] measured_corrected_delta;
wire [31:0] measured_uncorrectable_delta;
wire [31:0] measured_raw_score;

integer failures;

measured_control_estimator #(
    .WINDOW_CYCLES(WINDOW_CYCLES),
    .CORRECTED_WEIGHT(2),
    .UNCORRECTABLE_WEIGHT(1),
    .THRESHOLD_LEVEL1(8),
    .THRESHOLD_LEVEL2(22),
    .THRESHOLD_LEVEL3(36),
    .THRESHOLD_LEVEL4(50),
    .THRESHOLD_LEVEL5(65),
    .THRESHOLD_LEVEL6(79),
    .THRESHOLD_LEVEL7(93),
    .INITIAL_LEVEL(0)
) dut (
    .clk(clk),
    .rst(rst),
    .enable(enable),
    .corrected_error_count(corrected_error_count),
    .uncorrectable_error_count(uncorrectable_error_count),
    .measured_ctrl_level(measured_ctrl_level),
    .measured_ctrl_valid(measured_ctrl_valid),
    .measured_ctrl_update(measured_ctrl_update),
    .measured_window_count(measured_window_count),
    .measured_corrected_delta(measured_corrected_delta),
    .measured_uncorrectable_delta(measured_uncorrectable_delta),
    .measured_raw_score(measured_raw_score)
);

initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
end

task tick;
begin
    @(posedge clk);
    #1;
end
endtask

task wait_window;
    integer i;
begin
    for (i = 0; i < WINDOW_CYCLES; i = i + 1) begin
        tick();
    end
end
endtask

task check_eq32;
    input [31:0] actual;
    input [31:0] expected;
    input [511:0] name;
begin
    if (actual !== expected) begin
        $display("FAIL: %0s expected=%0d actual=%0d", name, expected, actual);
        failures = failures + 1;
    end else begin
        $display("PASS: %0s = %0d", name, actual);
    end
end
endtask

task check_eq3;
    input [2:0] actual;
    input [2:0] expected;
    input [511:0] name;
begin
    if (actual !== expected) begin
        $display("FAIL: %0s expected=%0d actual=%0d", name, expected, actual);
        failures = failures + 1;
    end else begin
        $display("PASS: %0s = %0d", name, actual);
    end
end
endtask

task check_eq1;
    input actual;
    input expected;
    input [511:0] name;
begin
    if (actual !== expected) begin
        $display("FAIL: %0s expected=%0d actual=%0d", name, expected, actual);
        failures = failures + 1;
    end else begin
        $display("PASS: %0s = %0d", name, actual);
    end
end
endtask

initial begin
    failures = 0;

    rst = 1'b1;
    enable = 1'b0;
    corrected_error_count = 32'd0;
    uncorrectable_error_count = 32'd0;

    tick();
    tick();

    rst = 1'b0;
    enable = 1'b1;

    /*
     * Reset state before the first measured window.
     */
    check_eq1(measured_ctrl_valid, 1'b0, "valid cleared after reset");
    check_eq1(measured_ctrl_update, 1'b0, "update cleared after reset");
    check_eq3(measured_ctrl_level, 3'd0, "initial level after reset");
    check_eq32(measured_window_count, 32'd0, "window count after reset");

    /*
     * Window 1: no errors.
     */
    wait_window();
    check_eq1(measured_ctrl_update, 1'b1, "update pulse after first window");
    check_eq1(measured_ctrl_valid, 1'b1, "valid after first window");
    check_eq32(measured_corrected_delta, 32'd0, "zero corrected delta");
    check_eq32(measured_uncorrectable_delta, 32'd0, "zero uncorrectable delta");
    check_eq32(measured_raw_score, 32'd0, "zero raw score");
    check_eq3(measured_ctrl_level, 3'd0, "zero score level");

    tick();
    check_eq1(measured_ctrl_update, 1'b0, "update pulse clears");

    /*
     * Window 2: corrected delta = 4.
     * raw_score = 2*4 + 0 = 8 -> level 1.
     */
    corrected_error_count = 32'd4;
    wait_window();
    check_eq32(measured_corrected_delta, 32'd4, "corrected delta 4");
    check_eq32(measured_uncorrectable_delta, 32'd0, "uncorrectable delta 0");
    check_eq32(measured_raw_score, 32'd8, "raw score 8");
    check_eq3(measured_ctrl_level, 3'd1, "threshold level 1");

    tick();

    /*
     * Window 3: uncorrectable delta = 22.
     * raw_score = 0 + 22 = 22 -> level 2.
     */
    uncorrectable_error_count = 32'd22;
    wait_window();
    check_eq32(measured_corrected_delta, 32'd0, "corrected delta 0");
    check_eq32(measured_uncorrectable_delta, 32'd22, "uncorrectable delta 22");
    check_eq32(measured_raw_score, 32'd22, "raw score 22");
    check_eq3(measured_ctrl_level, 3'd2, "threshold level 2");

    tick();

    /*
     * Window 4: combined corrected and DED deltas.
     * corrected delta = 10, uncorrectable delta = 16.
     * raw_score = 2*10 + 16 = 36 -> level 3.
     */
    corrected_error_count = 32'd14;
    uncorrectable_error_count = 32'd38;
    wait_window();
    check_eq32(measured_corrected_delta, 32'd10, "combined corrected delta 10");
    check_eq32(measured_uncorrectable_delta, 32'd16, "combined uncorrectable delta 16");
    check_eq32(measured_raw_score, 32'd36, "combined raw score 36");
    check_eq3(measured_ctrl_level, 3'd3, "combined threshold level 3");

    tick();

    /*
     * Window 5: large DED delta saturates at level 7.
     */
    uncorrectable_error_count = 32'd131;
    wait_window();
    check_eq32(measured_uncorrectable_delta, 32'd93, "uncorrectable delta 93");
    check_eq32(measured_raw_score, 32'd93, "raw score 93");
    check_eq3(measured_ctrl_level, 3'd7, "threshold level 7");

    tick();

    /*
     * Enable=0 must freeze the window and prevent update pulses.
     */
    enable = 1'b0;
    corrected_error_count = 32'd1000;
    uncorrectable_error_count = 32'd1000;

    tick();
    tick();
    tick();
    tick();
    tick();

    check_eq1(measured_ctrl_update, 1'b0, "no update while disabled");

    enable = 1'b1;

    /*
     * After re-enable, the accumulated counter delta is observed
     * at the next window boundary.
     */
    wait_window();
    check_eq32(measured_corrected_delta, 32'd986, "post-enable corrected delta 986");
    check_eq32(measured_uncorrectable_delta, 32'd869, "post-enable uncorrectable delta 869");
    check_eq3(measured_ctrl_level, 3'd7, "large post-enable delta saturates");

    if (failures != 0) begin
        $display("Measured control estimator test FAILED: %0d failure(s)", failures);
        $finish;
    end

    $display("Measured control estimator test PASSED");
    $finish;
end

endmodule

`timescale 1ns/1ps

module tb_interval_selector;

localparam LEVEL_WIDTH = 3;
localparam INTERVAL_WIDTH = 32;

localparam MODE_FIXED     = 2'd0;
localparam MODE_TABLE     = 2'd1;
localparam MODE_THRESHOLD = 2'd2;

reg clk;
reg rst;
reg enable;

reg [1:0] mode;

reg [LEVEL_WIDTH-1:0] ctrl_level;
reg ctrl_valid;
reg ctrl_update;

reg [INTERVAL_WIDTH-1:0] fixed_interval;
reg [INTERVAL_WIDTH-1:0] safe_interval;
reg [31:0] max_control_age;

reg [INTERVAL_WIDTH-1:0] level0_interval;
reg [INTERVAL_WIDTH-1:0] level1_interval;
reg [INTERVAL_WIDTH-1:0] level2_interval;
reg [INTERVAL_WIDTH-1:0] level3_interval;
reg [INTERVAL_WIDTH-1:0] level4_interval;
reg [INTERVAL_WIDTH-1:0] level5_interval;
reg [INTERVAL_WIDTH-1:0] level6_interval;
reg [INTERVAL_WIDTH-1:0] level7_interval;

reg [LEVEL_WIDTH-1:0] threshold_low_to_medium;
reg [LEVEL_WIDTH-1:0] threshold_medium_to_low;
reg [LEVEL_WIDTH-1:0] threshold_medium_to_high;
reg [LEVEL_WIDTH-1:0] threshold_high_to_medium;

reg [INTERVAL_WIDTH-1:0] threshold_low_interval;
reg [INTERVAL_WIDTH-1:0] threshold_medium_interval;
reg [INTERVAL_WIDTH-1:0] threshold_high_interval;

wire [INTERVAL_WIDTH-1:0] selected_interval;
wire safe_mode_active;
wire [LEVEL_WIDTH-1:0] current_level;
wire [1:0] threshold_state;
wire [31:0] control_age;

integer error_count;

interval_selector #(
    .LEVEL_WIDTH(LEVEL_WIDTH),
    .INTERVAL_WIDTH(INTERVAL_WIDTH)
) dut (
    .clk(clk),
    .rst(rst),
    .enable(enable),

    .mode(mode),

    .ctrl_level(ctrl_level),
    .ctrl_valid(ctrl_valid),
    .ctrl_update(ctrl_update),

    .fixed_interval(fixed_interval),
    .safe_interval(safe_interval),
    .max_control_age(max_control_age),

    .level0_interval(level0_interval),
    .level1_interval(level1_interval),
    .level2_interval(level2_interval),
    .level3_interval(level3_interval),
    .level4_interval(level4_interval),
    .level5_interval(level5_interval),
    .level6_interval(level6_interval),
    .level7_interval(level7_interval),

    .threshold_low_to_medium(threshold_low_to_medium),
    .threshold_medium_to_low(threshold_medium_to_low),
    .threshold_medium_to_high(threshold_medium_to_high),
    .threshold_high_to_medium(threshold_high_to_medium),

    .threshold_low_interval(threshold_low_interval),
    .threshold_medium_interval(threshold_medium_interval),
    .threshold_high_interval(threshold_high_interval),

    .selected_interval(selected_interval),
    .safe_mode_active(safe_mode_active),
    .current_level(current_level),
    .threshold_state(threshold_state),
    .control_age(control_age)
);

initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
end

task send_level_update;
    input [LEVEL_WIDTH-1:0] level_value;
    begin
        ctrl_level = level_value;
        ctrl_valid = 1'b1;
        ctrl_update = 1'b1;

        @(posedge clk);
        #1;

        ctrl_update = 1'b0;
    end
endtask

task wait_cycles;
    input integer count;
    integer k;
    begin
        for (k = 0; k < count; k = k + 1) begin
            @(posedge clk);
            #1;
        end
    end
endtask

task check_interval;
    input [INTERVAL_WIDTH-1:0] expected_interval;
    input [255:0] message;
    begin
        if (selected_interval !== expected_interval) begin
            $display("ERROR: wrong interval: %0s", message);
            $display("  expected = %0d", expected_interval);
            $display("  actual   = %0d", selected_interval);
            error_count = error_count + 1;
        end
    end
endtask

task check_safe;
    input expected_safe;
    input [255:0] message;
    begin
        if (safe_mode_active !== expected_safe) begin
            $display("ERROR: wrong safe_mode_active: %0s", message);
            $display("  expected = %0d", expected_safe);
            $display("  actual   = %0d", safe_mode_active);
            error_count = error_count + 1;
        end
    end
endtask

initial begin
    $dumpfile("results/logs/interval_selector.vcd");
    $dumpvars(0, tb_interval_selector);

    error_count = 0;

    rst = 1'b1;
    enable = 1'b0;

    mode = MODE_FIXED;

    ctrl_level = 3'd0;
    ctrl_valid = 1'b0;
    ctrl_update = 1'b0;

    fixed_interval = 32'd100;
    safe_interval = 32'd10;
    max_control_age = 32'd3;

    level0_interval = 32'd100;
    level1_interval = 32'd80;
    level2_interval = 32'd60;
    level3_interval = 32'd40;
    level4_interval = 32'd25;
    level5_interval = 32'd15;
    level6_interval = 32'd10;
    level7_interval = 32'd5;

    threshold_low_to_medium = 3'd3;
    threshold_medium_to_low = 3'd1;
    threshold_medium_to_high = 3'd6;
    threshold_high_to_medium = 3'd4;

    threshold_low_interval = 32'd100;
    threshold_medium_interval = 32'd40;
    threshold_high_interval = 32'd10;

    repeat (3) @(posedge clk);
    #1;

    rst = 1'b0;
    enable = 1'b1;

    /*
     * 1. Проверка режима постоянного интервала.
     */
    mode = MODE_FIXED;
    send_level_update(3'd5);
    check_interval(32'd100, "fixed mode must ignore ctrl_level");
    check_safe(1'b0, "after valid update safe mode must be inactive");

    /*
     * 2. Проверка табличной стратегии.
     */
    mode = MODE_TABLE;

    send_level_update(3'd0);
    check_interval(32'd100, "table level 0");

    send_level_update(3'd5);
    check_interval(32'd15, "table level 5");

    send_level_update(3'd7);
    check_interval(32'd5, "table level 7");

    /*
     * 3. Проверка пороговой стратегии с гистерезисом.
     */
    rst = 1'b1;
    @(posedge clk);
    #1;
    rst = 1'b0;
    enable = 1'b1;
    mode = MODE_THRESHOLD;

    send_level_update(3'd0);
    check_interval(32'd100, "threshold low state");

    send_level_update(3'd3);
    check_interval(32'd40, "threshold transition low to medium");

    send_level_update(3'd5);
    check_interval(32'd40, "threshold remains medium");

    send_level_update(3'd6);
    check_interval(32'd10, "threshold transition medium to high");

    send_level_update(3'd5);
    check_interval(32'd10, "threshold remains high due to hysteresis");

    send_level_update(3'd4);
    check_interval(32'd40, "threshold transition high to medium");

    send_level_update(3'd1);
    check_interval(32'd100, "threshold transition medium to low");

    /*
     * 4. Проверка безопасного режима при отсутствии обновления.
     */
    mode = MODE_TABLE;
    send_level_update(3'd2);
    check_interval(32'd60, "table level 2 before safe mode");
    check_safe(1'b0, "safe mode inactive before timeout");

    wait_cycles(5);

    check_safe(1'b1, "safe mode active after missed updates");
    check_interval(32'd10, "safe interval after missed updates");

    /*
     * 5. Проверка выхода из безопасного режима после нового обновления.
     */
    send_level_update(3'd1);
    check_safe(1'b0, "safe mode cleared after valid update");
    check_interval(32'd80, "table level 1 after safe mode cleared");

    if (error_count == 0) begin
        $display("Interval selector test passed.");
    end else begin
        $display("Interval selector test failed. Errors: %0d", error_count);
        $fatal(1);
    end

    $finish;
end

endmodule
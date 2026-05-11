`timescale 1ns/1ps

module tb_adaptive_safe_mode;

localparam ADDR_WIDTH = 4;
localparam CODEWORD_WIDTH = 39;
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

wire mem_read_en;
wire [ADDR_WIDTH-1:0] mem_read_addr;
wire [CODEWORD_WIDTH-1:0] mem_read_data;

wire mem_write_en;
wire [ADDR_WIDTH-1:0] mem_write_addr;
wire [CODEWORD_WIDTH-1:0] mem_write_data;

wire scrub_active;
wire [31:0] scrub_cycle_count;
wire [31:0] memory_read_count;
wire [31:0] memory_write_count;
wire [31:0] corrected_error_count;
wire [31:0] uncorrectable_error_count;
wire [31:0] interval_switch_count;

wire [INTERVAL_WIDTH-1:0] selected_interval;
wire safe_mode_active;
wire [LEVEL_WIDTH-1:0] current_level;
wire [1:0] threshold_state;
wire [31:0] control_age;

integer error_count;

protected_memory_model #(
    .ADDR_WIDTH(ADDR_WIDTH),
    .CODEWORD_WIDTH(CODEWORD_WIDTH)
) memory_inst (
    .clk(clk),

    .read_en(mem_read_en),
    .read_addr(mem_read_addr),
    .read_data(mem_read_data),

    .write_en(mem_write_en),
    .write_addr(mem_write_addr),
    .write_data(mem_write_data),

    .inject_en(1'b0),
    .inject_addr({ADDR_WIDTH{1'b0}}),
    .inject_bit(6'd0)
);

adaptive_scrub_controller #(
    .ADDR_WIDTH(ADDR_WIDTH),
    .CODEWORD_WIDTH(CODEWORD_WIDTH),
    .LEVEL_WIDTH(LEVEL_WIDTH),
    .INTERVAL_WIDTH(INTERVAL_WIDTH)
) controller_inst (
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

    .mem_read_en(mem_read_en),
    .mem_read_addr(mem_read_addr),
    .mem_read_data(mem_read_data),

    .mem_write_en(mem_write_en),
    .mem_write_addr(mem_write_addr),
    .mem_write_data(mem_write_data),

    .scrub_active(scrub_active),
    .scrub_cycle_count(scrub_cycle_count),
    .memory_read_count(memory_read_count),
    .memory_write_count(memory_write_count),
    .corrected_error_count(corrected_error_count),
    .uncorrectable_error_count(uncorrectable_error_count),
    .interval_switch_count(interval_switch_count),

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

task check_interval;
    input [INTERVAL_WIDTH-1:0] expected_interval;
    input [255:0] message;
    begin
        if (selected_interval !== expected_interval) begin
            $display("ERROR: wrong selected_interval: %0s", message);
            $display("  expected = %0d", expected_interval);
            $display("  actual   = %0d", selected_interval);
            error_count = error_count + 1;
        end
    end
endtask

task check_safe_mode;
    input expected_value;
    input [255:0] message;
    begin
        if (safe_mode_active !== expected_value) begin
            $display("ERROR: wrong safe_mode_active: %0s", message);
            $display("  expected = %0d", expected_value);
            $display("  actual   = %0d", safe_mode_active);
            error_count = error_count + 1;
        end
    end
endtask

initial begin
    $dumpfile("results/logs/adaptive_safe_mode.vcd");
    $dumpvars(0, tb_adaptive_safe_mode);

    error_count = 0;

    rst = 1'b1;
    enable = 1'b0;

    /*
     * Проверяем безопасный режим в табличном управлении.
     */
    mode = MODE_TABLE;

    ctrl_level = 3'd0;
    ctrl_valid = 1'b0;
    ctrl_update = 1'b0;

    /*
     * Обычный интервал для уровня 0 — 40 тактов.
     * Безопасный интервал — 5 тактов.
     *
     * Если управляющий сигнал пропал, контроллер должен перейти
     * с 40 тактов на 5 тактов.
     */
    fixed_interval = 32'd40;
    safe_interval = 32'd5;
    max_control_age = 32'd5;

    level0_interval = 32'd40;
    level1_interval = 32'd30;
    level2_interval = 32'd20;
    level3_interval = 32'd15;
    level4_interval = 32'd10;
    level5_interval = 32'd8;
    level6_interval = 32'd6;
    level7_interval = 32'd5;

    threshold_low_to_medium = 3'd3;
    threshold_medium_to_low = 3'd1;
    threshold_medium_to_high = 3'd6;
    threshold_high_to_medium = 3'd4;

    threshold_low_interval = 32'd40;
    threshold_medium_interval = 32'd15;
    threshold_high_interval = 32'd5;

    repeat (3) @(posedge clk);
    #1;

    rst = 1'b0;
    enable = 1'b1;

    /*
     * 1. Нормальное обновление управляющего уровня.
     */
    send_level_update(3'd0);

    check_safe_mode(1'b0, "after valid control update");
    check_interval(32'd40, "normal interval for level 0");

    /*
     * 2. Управляющий сигнал не обновляется.
     * Должен включиться безопасный режим.
     */
    wait_cycles(8);

    check_safe_mode(1'b1, "after missed control updates");
    check_interval(32'd5, "safe interval after timeout");

    /*
     * 3. Проверяем, что безопасный интервал реально используется:
     * при safe_interval = 5 контроллер должен запустить скраббинг.
     */
    wait (scrub_cycle_count == 32'd1);

    if (memory_read_count == 32'd0) begin
        $display("ERROR: scrub cycle did not read memory in safe mode");
        error_count = error_count + 1;
    end

    /*
     * 4. Новое корректное обновление должно вывести контроллер
     * из безопасного режима.
     */
    send_level_update(3'd2);

    check_safe_mode(1'b0, "after restored control update");
    check_interval(32'd20, "normal interval for level 2 after restore");

    /*
     * 5. Ошибок в память не вносили, поэтому счётчики ошибок
     * должны оставаться нулевыми.
     */
    if (corrected_error_count !== 32'd0) begin
        $display("ERROR: corrected_error_count must be zero");
        $display("  actual = %0d", corrected_error_count);
        error_count = error_count + 1;
    end

    if (uncorrectable_error_count !== 32'd0) begin
        $display("ERROR: uncorrectable_error_count must be zero");
        $display("  actual = %0d", uncorrectable_error_count);
        error_count = error_count + 1;
    end

    if (error_count == 0) begin
        $display("Adaptive safe mode test passed.");
    end else begin
        $display("Adaptive safe mode test failed. Errors: %0d", error_count);
        $fatal(1);
    end

    $finish;
end

endmodule
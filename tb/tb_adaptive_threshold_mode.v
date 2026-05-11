`timescale 1ns/1ps

module tb_adaptive_threshold_mode;

localparam ADDR_WIDTH = 4;
localparam CODEWORD_WIDTH = 39;
localparam LEVEL_WIDTH = 3;
localparam INTERVAL_WIDTH = 32;

localparam MODE_FIXED     = 2'd0;
localparam MODE_TABLE     = 2'd1;
localparam MODE_THRESHOLD = 2'd2;

localparam STATE_LOW    = 2'd0;
localparam STATE_MEDIUM = 2'd1;
localparam STATE_HIGH   = 2'd2;

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

task check_state_and_interval;
    input [1:0] expected_state;
    input [INTERVAL_WIDTH-1:0] expected_interval;
    input [255:0] message;
    begin
        if (threshold_state !== expected_state) begin
            $display("ERROR: wrong threshold_state: %0s", message);
            $display("  expected state = %0d", expected_state);
            $display("  actual state   = %0d", threshold_state);
            error_count = error_count + 1;
        end

        if (selected_interval !== expected_interval) begin
            $display("ERROR: wrong selected_interval: %0s", message);
            $display("  expected interval = %0d", expected_interval);
            $display("  actual interval   = %0d", selected_interval);
            error_count = error_count + 1;
        end
    end
endtask

task wait_for_scrub_cycle;
    input [31:0] expected_count;
    integer timeout;
    begin
        timeout = 0;

        while ((scrub_cycle_count < expected_count) && (timeout < 5000)) begin
            @(posedge clk);
            #1;
            timeout = timeout + 1;
        end

        if (scrub_cycle_count < expected_count) begin
            $display("ERROR: timeout while waiting for scrub cycle %0d", expected_count);
            error_count = error_count + 1;
        end
    end
endtask

initial begin
    $dumpfile("results/logs/adaptive_threshold_mode.vcd");
    $dumpvars(0, tb_adaptive_threshold_mode);

    error_count = 0;

    rst = 1'b1;
    enable = 1'b0;

    /*
     * Проверяем трёхрежимное управление.
     */
    mode = MODE_THRESHOLD;

    ctrl_level = 3'd0;
    ctrl_valid = 1'b0;
    ctrl_update = 1'b0;

    /*
     * Эти интервалы задаются для табличного режима.
     * В данной проверке они не являются основными,
     * но входы должны иметь определённые значения.
     */
    fixed_interval = 32'd40;
    safe_interval = 32'd5;
    max_control_age = 32'd1000;

    level0_interval = 32'd40;
    level1_interval = 32'd30;
    level2_interval = 32'd20;
    level3_interval = 32'd15;
    level4_interval = 32'd10;
    level5_interval = 32'd8;
    level6_interval = 32'd6;
    level7_interval = 32'd5;

    /*
     * Пороговая схема с гистерезисом:
     *
     * LOW    -> MEDIUM при уровне >= 3
     * MEDIUM -> LOW    при уровне <= 1
     *
     * MEDIUM -> HIGH   при уровне >= 6
     * HIGH   -> MEDIUM при уровне <= 4
     */
    threshold_low_to_medium = 3'd3;
    threshold_medium_to_low = 3'd1;
    threshold_medium_to_high = 3'd6;
    threshold_high_to_medium = 3'd4;

    /*
     * Интервалы трёх режимов:
     *
     * LOW    — фоновый режим, редкий скраббинг;
     * MEDIUM — промежуточный режим;
     * HIGH   — динамический/высокий режим, частый скраббинг.
     */
    threshold_low_interval = 32'd30;
    threshold_medium_interval = 32'd12;
    threshold_high_interval = 32'd5;

    repeat (3) @(posedge clk);
    #1;

    rst = 1'b0;
    enable = 1'b1;

    /*
     * 1. Фоновый режим.
     */
    send_level_update(3'd0);
    check_state_and_interval(STATE_LOW, 32'd30, "background mode at level 0");

    /*
     * Подтверждаем, что контроллер выполняет скраббинг
     * с выбранным интервалом фонового режима.
     */
    wait_for_scrub_cycle(32'd1);

    if (memory_read_count < 32'd16) begin
        $display("ERROR: first scrub cycle did not read all memory words");
        $display("  memory_read_count = %0d", memory_read_count);
        error_count = error_count + 1;
    end

    /*
     * 2. Переход в промежуточный режим.
     */
    send_level_update(3'd3);
    check_state_and_interval(STATE_MEDIUM, 32'd12, "transition background to intermediate");

    /*
     * 3. Уровень 5 не должен переводить систему в высокий режим.
     * Это проверка гистерезиса и порога перехода MEDIUM -> HIGH.
     */
    send_level_update(3'd5);
    check_state_and_interval(STATE_MEDIUM, 32'd12, "remain in intermediate at level 5");

    /*
     * 4. Переход в высокий режим.
     */
    send_level_update(3'd6);
    check_state_and_interval(STATE_HIGH, 32'd5, "transition intermediate to high");

    wait_for_scrub_cycle(32'd2);

    /*
     * 5. Уровень 5 не должен сразу вернуть систему в промежуточный режим.
     * Возврат HIGH -> MEDIUM должен быть только при уровне <= 4.
     */
    send_level_update(3'd5);
    check_state_and_interval(STATE_HIGH, 32'd5, "remain in high due to hysteresis");

    /*
     * 6. Переход из высокого режима в промежуточный.
     */
    send_level_update(3'd4);
    check_state_and_interval(STATE_MEDIUM, 32'd12, "transition high to intermediate");

    /*
     * 7. Переход из промежуточного режима в фоновый.
     */
    send_level_update(3'd1);
    check_state_and_interval(STATE_LOW, 32'd30, "transition intermediate to background");

    /*
     * 8. Безопасный режим не должен был включаться:
     * управляющий сигнал обновлялся регулярно.
     */
    if (safe_mode_active !== 1'b0) begin
        $display("ERROR: safe mode must remain inactive in threshold-mode test");
        error_count = error_count + 1;
    end

    /*
     * 9. Ошибки в память не вносились.
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

    /*
     * 10. Должен быть как минимум один переход интервала.
     * Точное значение зависит от моментов обновления и начальной фиксации,
     * поэтому проверяем не строгое число, а сам факт переключений.
     */
    if (interval_switch_count == 32'd0) begin
        $display("ERROR: interval_switch_count must be greater than zero");
        error_count = error_count + 1;
    end

    if (error_count == 0) begin
        $display("Adaptive threshold mode test passed.");
    end else begin
        $display("Adaptive threshold mode test failed. Errors: %0d", error_count);
        $fatal(1);
    end

    $finish;
end

endmodule
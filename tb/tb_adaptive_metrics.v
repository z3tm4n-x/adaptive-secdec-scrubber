`timescale 1ns/1ps

module tb_adaptive_metrics;

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

wire [31:0] total_cycle_count;
wire [31:0] scrub_active_cycle_count;
wire [31:0] memory_busy_cycle_count;
wire [31:0] safe_mode_cycle_count;
wire [31:0] safe_mode_entry_count;

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

    .total_cycle_count(total_cycle_count),
    .scrub_active_cycle_count(scrub_active_cycle_count),
    .memory_busy_cycle_count(memory_busy_cycle_count),
    .safe_mode_cycle_count(safe_mode_cycle_count),
    .safe_mode_entry_count(safe_mode_entry_count),

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

initial begin
    $dumpfile("results/logs/adaptive_metrics.vcd");
    $dumpvars(0, tb_adaptive_metrics);

    error_count = 0;

    rst = 1'b1;
    enable = 1'b0;

    mode = MODE_TABLE;

    ctrl_level = 3'd0;
    ctrl_valid = 1'b0;
    ctrl_update = 1'b0;

    /*
     * Обычный интервал для уровня 0 — 20 тактов.
     * Безопасный интервал — 5 тактов.
     */
    fixed_interval = 32'd20;
    safe_interval = 32'd5;
    max_control_age = 32'd5;

    level0_interval = 32'd20;
    level1_interval = 32'd18;
    level2_interval = 32'd15;
    level3_interval = 32'd12;
    level4_interval = 32'd10;
    level5_interval = 32'd8;
    level6_interval = 32'd6;
    level7_interval = 32'd5;

    threshold_low_to_medium = 3'd3;
    threshold_medium_to_low = 3'd1;
    threshold_medium_to_high = 3'd6;
    threshold_high_to_medium = 3'd4;

    threshold_low_interval = 32'd20;
    threshold_medium_interval = 32'd10;
    threshold_high_interval = 32'd5;

    repeat (3) @(posedge clk);
    #1;

    rst = 1'b0;
    enable = 1'b1;

    /*
     * 1. Нормальное обновление.
     */
    send_level_update(3'd0);

    if (selected_interval !== 32'd20) begin
        $display("ERROR: expected selected_interval = 20 after level 0 update");
        $display("  actual = %0d", selected_interval);
        error_count = error_count + 1;
    end

    /*
     * 2. Ждём исчезновения актуальности управляющего сигнала.
     */
    wait_cycles(8);

    if (safe_mode_active !== 1'b1) begin
        $display("ERROR: safe_mode_active must be 1 after control timeout");
        error_count = error_count + 1;
    end

    if (selected_interval !== 32'd5) begin
        $display("ERROR: expected selected_interval = safe_interval");
        $display("  actual = %0d", selected_interval);
        error_count = error_count + 1;
    end

    /*
     * 3. Дожидаемся полного цикла скраббинга.
     */
    wait (scrub_cycle_count == 32'd1);

    /*
     * 4. Проверяем новые счётчики.
     */
    if (total_cycle_count == 32'd0) begin
        $display("ERROR: total_cycle_count must be greater than zero");
        error_count = error_count + 1;
    end

    if (scrub_active_cycle_count == 32'd0) begin
        $display("ERROR: scrub_active_cycle_count must be greater than zero");
        error_count = error_count + 1;
    end

    if (memory_busy_cycle_count == 32'd0) begin
        $display("ERROR: memory_busy_cycle_count must be greater than zero");
        error_count = error_count + 1;
    end

    if (safe_mode_cycle_count == 32'd0) begin
        $display("ERROR: safe_mode_cycle_count must be greater than zero");
        error_count = error_count + 1;
    end

    if (safe_mode_entry_count !== 32'd1) begin
        $display("ERROR: safe_mode_entry_count must be 1");
        $display("  actual = %0d", safe_mode_entry_count);
        error_count = error_count + 1;
    end

    /*
     * В этом тесте память только читается, ошибок нет.
     * Поэтому число занятых тактов памяти должно быть не меньше числа чтений.
     */
    if (memory_busy_cycle_count < memory_read_count) begin
        $display("ERROR: memory_busy_cycle_count must be >= memory_read_count");
        $display("  busy  = %0d", memory_busy_cycle_count);
        $display("  reads = %0d", memory_read_count);
        error_count = error_count + 1;
    end

    /*
     * Ошибок не вносили.
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
     * Печатаем значения, которые позже будут использоваться
     * в сравнении стратегий.
     */
    $display("METRICS:");
    $display("  total_cycle_count        = %0d", total_cycle_count);
    $display("  scrub_active_cycle_count = %0d", scrub_active_cycle_count);
    $display("  memory_busy_cycle_count  = %0d", memory_busy_cycle_count);
    $display("  safe_mode_cycle_count    = %0d", safe_mode_cycle_count);
    $display("  safe_mode_entry_count    = %0d", safe_mode_entry_count);
    $display("  scrub_cycle_count        = %0d", scrub_cycle_count);
    $display("  memory_read_count        = %0d", memory_read_count);
    $display("  memory_write_count       = %0d", memory_write_count);

    if (error_count == 0) begin
        $display("Adaptive metrics test passed.");
    end else begin
        $display("Adaptive metrics test failed. Errors: %0d", error_count);
        $fatal(1);
    end

    $finish;
end

endmodule
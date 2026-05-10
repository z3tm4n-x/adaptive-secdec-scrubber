`timescale 1ns/1ps

module tb_adaptive_scrub_controller;

localparam ADDR_WIDTH = 4;
localparam CODEWORD_WIDTH = 39;
localparam LEVEL_WIDTH = 3;
localparam INTERVAL_WIDTH = 32;
localparam DEPTH = (1 << ADDR_WIDTH);

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

wire ctrl_read_en;
wire [ADDR_WIDTH-1:0] ctrl_read_addr;
wire [CODEWORD_WIDTH-1:0] mem_read_data;

wire ctrl_write_en;
wire [ADDR_WIDTH-1:0] ctrl_write_addr;
wire [CODEWORD_WIDTH-1:0] ctrl_write_data;

reg tb_mode;

reg tb_read_en;
reg [ADDR_WIDTH-1:0] tb_read_addr;

reg tb_write_en;
reg [ADDR_WIDTH-1:0] tb_write_addr;
reg [CODEWORD_WIDTH-1:0] tb_write_data;

reg tb_inject_en;
reg [ADDR_WIDTH-1:0] tb_inject_addr;
reg [5:0] tb_inject_bit;

wire mem_read_en;
wire [ADDR_WIDTH-1:0] mem_read_addr;

wire mem_write_en;
wire [ADDR_WIDTH-1:0] mem_write_addr;
wire [CODEWORD_WIDTH-1:0] mem_write_data;

assign mem_read_en   = tb_mode ? tb_read_en   : ctrl_read_en;
assign mem_read_addr = tb_mode ? tb_read_addr : ctrl_read_addr;

assign mem_write_en   = tb_mode ? tb_write_en   : ctrl_write_en;
assign mem_write_addr = tb_mode ? tb_write_addr : ctrl_write_addr;
assign mem_write_data = tb_mode ? tb_write_data : ctrl_write_data;

reg [31:0] encoder_data_in;
wire [38:0] encoded_codeword;

wire [38:0] checked_corrected_codeword;
wire [31:0] checked_data_out;
wire checked_single_error;
wire checked_double_error;
wire checked_uncorrectable;
wire [5:0] checked_error_position;

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

reg [31:0] expected_data [0:DEPTH-1];

integer i;
integer error_count;

secded_32_39_encoder encoder_inst (
    .data_in(encoder_data_in),
    .codeword_out(encoded_codeword)
);

secded_32_39_decoder checker_decoder_inst (
    .codeword_in(mem_read_data),
    .codeword_corrected(checked_corrected_codeword),
    .data_out(checked_data_out),
    .single_error(checked_single_error),
    .double_error(checked_double_error),
    .uncorrectable(checked_uncorrectable),
    .error_position(checked_error_position)
);

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

    .inject_en(tb_inject_en),
    .inject_addr(tb_inject_addr),
    .inject_bit(tb_inject_bit)
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

    .mem_read_en(ctrl_read_en),
    .mem_read_addr(ctrl_read_addr),
    .mem_read_data(mem_read_data),

    .mem_write_en(ctrl_write_en),
    .mem_write_addr(ctrl_write_addr),
    .mem_write_data(ctrl_write_data),

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

task write_memory_word;
    input [ADDR_WIDTH-1:0] addr;
    input [31:0] data;
    begin
        encoder_data_in = data;
        #1;

        tb_write_addr = addr;
        tb_write_data = encoded_codeword;
        tb_write_en = 1'b1;

        @(posedge clk);
        #1;

        tb_write_en = 1'b0;
        expected_data[addr] = data;
    end
endtask

task read_memory_word;
    input [ADDR_WIDTH-1:0] addr;
    begin
        tb_read_addr = addr;
        tb_read_en = 1'b1;

        @(posedge clk);
        #1;

        tb_read_en = 1'b0;
    end
endtask

task inject_error;
    input [ADDR_WIDTH-1:0] addr;
    input [5:0] bit_index;
    begin
        tb_inject_addr = addr;
        tb_inject_bit = bit_index;
        tb_inject_en = 1'b1;

        @(posedge clk);
        #1;

        tb_inject_en = 1'b0;
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
    $dumpfile("results/logs/adaptive_scrub_controller.vcd");
    $dumpvars(0, tb_adaptive_scrub_controller);

    error_count = 0;

    rst = 1'b1;
    enable = 1'b0;

    mode = MODE_TABLE;

    ctrl_level = 3'd0;
    ctrl_valid = 1'b0;
    ctrl_update = 1'b0;

    fixed_interval = 32'd40;
    safe_interval = 32'd5;
    max_control_age = 32'd100;

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

    tb_mode = 1'b1;

    tb_read_en = 1'b0;
    tb_read_addr = {ADDR_WIDTH{1'b0}};

    tb_write_en = 1'b0;
    tb_write_addr = {ADDR_WIDTH{1'b0}};
    tb_write_data = {CODEWORD_WIDTH{1'b0}};

    tb_inject_en = 1'b0;
    tb_inject_addr = {ADDR_WIDTH{1'b0}};
    tb_inject_bit = 6'd0;

    encoder_data_in = 32'd0;

    repeat (3) @(posedge clk);

    /*
     * 1. Записываем исходные данные.
     */
    for (i = 0; i < DEPTH; i = i + 1) begin
        write_memory_word(i[ADDR_WIDTH-1:0], 32'h3000_0000 + i);
    end

    /*
     * 2. Вносим две одиночные ошибки в разные слова.
     */
    inject_error(4'd3, 6'd5);
    inject_error(4'd7, 6'd10);

    /*
     * 3. Вносим две ошибки в одно слово.
     */
    inject_error(4'd12, 6'd2);
    inject_error(4'd12, 6'd4);

    /*
     * 4. Передаём управление памятью контроллеру.
     */
    tb_mode = 1'b0;

    rst = 1'b0;
    enable = 1'b1;

    /*
     * 5. Сначала задаём низкий уровень.
     */
    send_level_update(3'd0);

    if (selected_interval !== 32'd40) begin
        $display("ERROR: selected_interval must be 40 at level 0");
        $display("  actual = %0d", selected_interval);
        error_count = error_count + 1;
    end

    /*
     * 6. Затем задаём высокий уровень.
     * Интервал должен уменьшиться.
     */
    send_level_update(3'd7);

    if (selected_interval !== 32'd5) begin
        $display("ERROR: selected_interval must be 5 at level 7");
        $display("  actual = %0d", selected_interval);
        error_count = error_count + 1;
    end

    /*
     * 7. Ждём завершения одного полного цикла скраббинга.
     */
    wait (scrub_cycle_count == 32'd1);

    enable = 1'b0;

    repeat (3) @(posedge clk);

    /*
     * 8. Проверяем счётчики.
     */
    if (memory_read_count !== DEPTH) begin
        $display("ERROR: wrong memory_read_count");
        $display("  expected = %0d", DEPTH);
        $display("  actual   = %0d", memory_read_count);
        error_count = error_count + 1;
    end

    if (memory_write_count !== 32'd2) begin
        $display("ERROR: wrong memory_write_count");
        $display("  expected = 2");
        $display("  actual   = %0d", memory_write_count);
        error_count = error_count + 1;
    end

    if (corrected_error_count !== 32'd2) begin
        $display("ERROR: wrong corrected_error_count");
        $display("  expected = 2");
        $display("  actual   = %0d", corrected_error_count);
        error_count = error_count + 1;
    end

    if (uncorrectable_error_count !== 32'd1) begin
        $display("ERROR: wrong uncorrectable_error_count");
        $display("  expected = 1");
        $display("  actual   = %0d", uncorrectable_error_count);
        error_count = error_count + 1;
    end

    /*
     * 9. Проверяем память после работы контроллера.
     */
    tb_mode = 1'b1;

    read_memory_word(4'd3);

    if (checked_data_out !== expected_data[3] ||
        checked_single_error !== 1'b0 ||
        checked_double_error !== 1'b0 ||
        checked_uncorrectable !== 1'b0) begin

        $display("ERROR: address 3 was not corrected properly");
        error_count = error_count + 1;
    end

    read_memory_word(4'd7);

    if (checked_data_out !== expected_data[7] ||
        checked_single_error !== 1'b0 ||
        checked_double_error !== 1'b0 ||
        checked_uncorrectable !== 1'b0) begin

        $display("ERROR: address 7 was not corrected properly");
        error_count = error_count + 1;
    end

    read_memory_word(4'd12);

    if (checked_single_error !== 1'b0 ||
        checked_double_error !== 1'b1 ||
        checked_uncorrectable !== 1'b1) begin

        $display("ERROR: address 12 is not reported as uncorrectable");
        error_count = error_count + 1;
    end

    if (error_count == 0) begin
        $display("Adaptive scrub controller test passed.");
    end else begin
        $display("Adaptive scrub controller test failed. Errors: %0d", error_count);
        $fatal(1);
    end

    $finish;
end

endmodule
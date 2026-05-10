`timescale 1ns/1ps

module tb_fixed_scrub_controller;

localparam ADDR_WIDTH = 4;
localparam CODEWORD_WIDTH = 39;
localparam DEPTH = (1 << ADDR_WIDTH);
localparam INTERVAL_CYCLES = 20;

reg clk;
reg rst;
reg enable;

/*
 * Сигналы контроллера к памяти.
 */
wire ctrl_read_en;
wire [ADDR_WIDTH-1:0] ctrl_read_addr;
wire [CODEWORD_WIDTH-1:0] mem_read_data;

wire ctrl_write_en;
wire [ADDR_WIDTH-1:0] ctrl_write_addr;
wire [CODEWORD_WIDTH-1:0] ctrl_write_data;

/*
 * Служебные сигналы проверочной среды.
 * Они используются для начальной записи, чтения и внесения ошибок.
 */
reg tb_mode;

reg tb_read_en;
reg [ADDR_WIDTH-1:0] tb_read_addr;

reg tb_write_en;
reg [ADDR_WIDTH-1:0] tb_write_addr;
reg [CODEWORD_WIDTH-1:0] tb_write_data;

reg tb_inject_en;
reg [ADDR_WIDTH-1:0] tb_inject_addr;
reg [5:0] tb_inject_bit;

/*
 * Итоговые сигналы, которые подаются на модель памяти.
 * Пока tb_mode = 1, памятью управляет проверочная среда.
 * Пока tb_mode = 0, памятью управляет контроллер скраббинга.
 */
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

/*
 * Кодер нужен проверочной среде для начальной записи данных в память.
 */
reg [31:0] encoder_data_in;
wire [38:0] encoded_codeword;

/*
 * Декодер нужен проверочной среде для проверки состояния памяти
 * после работы контроллера.
 */
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

reg [31:0] expected_data [0:DEPTH-1];
reg [38:0] expected_codeword [0:DEPTH-1];

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

fixed_scrub_controller #(
    .ADDR_WIDTH(ADDR_WIDTH),
    .CODEWORD_WIDTH(CODEWORD_WIDTH),
    .INTERVAL_CYCLES(INTERVAL_CYCLES)
) controller_inst (
    .clk(clk),
    .rst(rst),
    .enable(enable),

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
    .uncorrectable_error_count(uncorrectable_error_count)
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
        expected_codeword[addr] = encoded_codeword;
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

initial begin
    $dumpfile("results/logs/fixed_scrub_controller.vcd");
    $dumpvars(0, tb_fixed_scrub_controller);

    rst = 1'b1;
    enable = 1'b0;

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
    error_count = 0;

    /*
     * Небольшая пауза после начала моделирования.
     */
    repeat (3) @(posedge clk);

    /*
     * 1. Начальная запись 16 слов в память.
     */
    for (i = 0; i < DEPTH; i = i + 1) begin
        write_memory_word(i[ADDR_WIDTH-1:0], 32'h2000_0000 + i);
    end

    /*
     * 2. Вносим две одиночные ошибки в разные слова.
     * Эти ошибки должны быть исправлены контроллером.
     */
    inject_error(4'd3, 6'd5);
    inject_error(4'd7, 6'd10);

    /*
     * 3. Вносим две ошибки в одно слово.
     * Это должна быть неустранимая ошибка.
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
     * 5. Ждём завершения одного полного цикла скраббинга.
     */
    wait (scrub_cycle_count == 32'd1);

    /*
     * Останавливаем контроллер, но не сбрасываем его счётчики.
     */
    enable = 1'b0;

    repeat (3) @(posedge clk);

    /*
     * 6. Проверяем счётчики контроллера.
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
     * 7. Возвращаем управление памятью проверочной среде
     * и читаем исправленные слова.
     */
    tb_mode = 1'b1;

    /*
     * Адрес 3 должен быть исправлен.
     */
    read_memory_word(4'd3);

    if (checked_data_out !== expected_data[3] ||
        checked_single_error !== 1'b0 ||
        checked_double_error !== 1'b0 ||
        checked_uncorrectable !== 1'b0) begin

        $display("ERROR: address 3 was not corrected properly");
        $display("  data = 0x%08h", checked_data_out);
        $display("  single_error = %0d", checked_single_error);
        $display("  double_error = %0d", checked_double_error);
        $display("  uncorrectable = %0d", checked_uncorrectable);
        error_count = error_count + 1;
    end

    /*
     * Адрес 7 должен быть исправлен.
     */
    read_memory_word(4'd7);

    if (checked_data_out !== expected_data[7] ||
        checked_single_error !== 1'b0 ||
        checked_double_error !== 1'b0 ||
        checked_uncorrectable !== 1'b0) begin

        $display("ERROR: address 7 was not corrected properly");
        $display("  data = 0x%08h", checked_data_out);
        $display("  single_error = %0d", checked_single_error);
        $display("  double_error = %0d", checked_double_error);
        $display("  uncorrectable = %0d", checked_uncorrectable);
        error_count = error_count + 1;
    end

    /*
     * Адрес 12 должен остаться неустранимым.
     */
    read_memory_word(4'd12);

    if (checked_single_error !== 1'b0 ||
        checked_double_error !== 1'b1 ||
        checked_uncorrectable !== 1'b1) begin

        $display("ERROR: address 12 is not reported as uncorrectable");
        $display("  single_error = %0d", checked_single_error);
        $display("  double_error = %0d", checked_double_error);
        $display("  uncorrectable = %0d", checked_uncorrectable);
        error_count = error_count + 1;
    end

    if (error_count == 0) begin
        $display("Fixed scrub controller test passed.");
    end else begin
        $display("Fixed scrub controller test failed. Errors: %0d", error_count);
        $fatal(1);
    end

    $finish;
end

endmodule
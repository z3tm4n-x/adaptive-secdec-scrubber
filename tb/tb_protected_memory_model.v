`timescale 1ns/1ps

module tb_protected_memory_model;

localparam ADDR_WIDTH = 4;
localparam CODEWORD_WIDTH = 39;
localparam DEPTH = (1 << ADDR_WIDTH);

reg clk;

reg read_en;
reg [ADDR_WIDTH-1:0] read_addr;
wire [CODEWORD_WIDTH-1:0] read_data;

reg write_en;
reg [ADDR_WIDTH-1:0] write_addr;
reg [CODEWORD_WIDTH-1:0] write_data;

reg inject_en;
reg [ADDR_WIDTH-1:0] inject_addr;
reg [5:0] inject_bit;

reg inject_mask_en;
reg [ADDR_WIDTH-1:0] inject_mask_addr;
reg [CODEWORD_WIDTH-1:0] inject_mask;

reg [31:0] encoder_data_in;
wire [38:0] encoded_codeword;

wire [38:0] corrected_codeword;
wire [31:0] decoded_data;
wire single_error;
wire double_error;
wire uncorrectable;
wire [5:0] error_position;

reg [31:0] expected_data [0:DEPTH-1];
reg [38:0] expected_codeword [0:DEPTH-1];

integer i;
integer error_count;
reg [CODEWORD_WIDTH-1:0] expected_masked_codeword;

secded_32_39_encoder encoder_inst (
    .data_in(encoder_data_in),
    .codeword_out(encoded_codeword)
);

secded_32_39_decoder decoder_inst (
    .codeword_in(read_data),
    .codeword_corrected(corrected_codeword),
    .data_out(decoded_data),
    .single_error(single_error),
    .double_error(double_error),
    .uncorrectable(uncorrectable),
    .error_position(error_position)
);

protected_memory_model #(
    .ADDR_WIDTH(ADDR_WIDTH),
    .CODEWORD_WIDTH(CODEWORD_WIDTH)
) memory_inst (
    .clk(clk),

    .read_en(read_en),
    .read_addr(read_addr),
    .read_data(read_data),

    .write_en(write_en),
    .write_addr(write_addr),
    .write_data(write_data),

    .inject_en(inject_en),
    .inject_addr(inject_addr),
    .inject_bit(inject_bit),

    .inject_mask_en(inject_mask_en),
    .inject_mask_addr(inject_mask_addr),
    .inject_mask(inject_mask)
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

        write_addr = addr;
        write_data = encoded_codeword;
        write_en = 1'b1;

        @(posedge clk);
        #1;

        write_en = 1'b0;
        expected_data[addr] = data;
        expected_codeword[addr] = encoded_codeword;
    end
endtask

task read_memory_word;
    input [ADDR_WIDTH-1:0] addr;
    begin
        read_addr = addr;
        read_en = 1'b1;

        @(posedge clk);
        #1;

        read_en = 1'b0;
    end
endtask

task inject_single_bit_error;
    input [ADDR_WIDTH-1:0] addr;
    input [5:0] bit_index;
    begin
        inject_addr = addr;
        inject_bit = bit_index;
        inject_en = 1'b1;

        @(posedge clk);
        #1;

        inject_en = 1'b0;
    end
endtask

task inject_mask_error;
    input [ADDR_WIDTH-1:0] addr;
    input [CODEWORD_WIDTH-1:0] mask;
    begin
        inject_mask_addr = addr;
        inject_mask = mask;
        inject_mask_en = 1'b1;

        @(posedge clk);
        #1;

        inject_mask_en = 1'b0;
        inject_mask = {CODEWORD_WIDTH{1'b0}};
    end
endtask

initial begin
    $dumpfile("results/logs/protected_memory_model.vcd");
    $dumpvars(0, tb_protected_memory_model);

    read_en = 1'b0;
    read_addr = {ADDR_WIDTH{1'b0}};

    write_en = 1'b0;
    write_addr = {ADDR_WIDTH{1'b0}};
    write_data = {CODEWORD_WIDTH{1'b0}};

    inject_en = 1'b0;
    inject_addr = {ADDR_WIDTH{1'b0}};
    inject_bit = 6'd0;

    inject_mask_en = 1'b0;
    inject_mask_addr = {ADDR_WIDTH{1'b0}};
    inject_mask = {CODEWORD_WIDTH{1'b0}};

    encoder_data_in = 32'd0;
    error_count = 0;

    /*
     * 1. Записываем в память 16 слов.
     */
    for (i = 0; i < DEPTH; i = i + 1) begin
        write_memory_word(i[ADDR_WIDTH-1:0], 32'h1000_0000 + i);
    end

    /*
     * 2. Читаем все слова и проверяем, что они декодируются без ошибок.
     */
    for (i = 0; i < DEPTH; i = i + 1) begin
        read_memory_word(i[ADDR_WIDTH-1:0]);

        if (decoded_data !== expected_data[i]) begin
            $display("ERROR: read data mismatch before injection at address %0d", i);
            $display("  expected data = 0x%08h", expected_data[i]);
            $display("  actual data   = 0x%08h", decoded_data);
            error_count = error_count + 1;
        end

        if (single_error !== 1'b0 ||
            double_error !== 1'b0 ||
            uncorrectable !== 1'b0) begin
            $display("ERROR: unexpected error flags before injection at address %0d", i);
            error_count = error_count + 1;
        end
    end

    /*
     * 3. Вносим одиночную ошибку:
     * адрес 3, бит 5.
     */
    inject_single_bit_error(4'd3, 6'd5);

    /*
     * 4. Читаем адрес 3.
     * Декодер должен обнаружить и исправить одиночную ошибку.
     */
    read_memory_word(4'd3);

    if (decoded_data !== expected_data[3]) begin
        $display("ERROR: decoded data mismatch after single-bit injection");
        $display("  expected data = 0x%08h", expected_data[3]);
        $display("  actual data   = 0x%08h", decoded_data);
        error_count = error_count + 1;
    end

    if (single_error !== 1'b1 ||
        double_error !== 1'b0 ||
        uncorrectable !== 1'b0 ||
        error_position !== 6'd6) begin

        $display("ERROR: wrong flags after single-bit injection");
        $display("  single_error   = %0d", single_error);
        $display("  double_error   = %0d", double_error);
        $display("  uncorrectable  = %0d", uncorrectable);
        $display("  error_position = %0d", error_position);
        error_count = error_count + 1;
    end

    /*
     * 5. Вносим вторую ошибку в то же слово:
     * адрес 3, бит 10.
     * Теперь в слове две ошибки.
     */
    inject_single_bit_error(4'd3, 6'd10);

    read_memory_word(4'd3);

    if (single_error !== 1'b0 ||
        double_error !== 1'b1 ||
        uncorrectable !== 1'b1) begin

        $display("ERROR: wrong flags after double-bit injection");
        $display("  single_error  = %0d", single_error);
        $display("  double_error  = %0d", double_error);
        $display("  uncorrectable = %0d", uncorrectable);
        error_count = error_count + 1;
    end

    /*
     * 6. Проверяем мгновенный двухбитовый кластер через маску.
     * Берём свежий адрес 4, чтобы проверка не зависела от предыдущих
     * накопленных ошибок в адресе 3.
     */
    expected_masked_codeword = expected_codeword[4] ^ ((39'd1 << 2) | (39'd1 << 11));

    inject_mask_error(
        4'd4,
        ((39'd1 << 2) | (39'd1 << 11))
    );

    read_memory_word(4'd4);

    if (read_data !== expected_masked_codeword) begin
        $display("ERROR: memory content mismatch after mask injection");
        $display("  expected codeword = 0x%010h", expected_masked_codeword);
        $display("  actual codeword   = 0x%010h", read_data);
        error_count = error_count + 1;
    end

    if (single_error !== 1'b0 ||
        double_error !== 1'b1 ||
        uncorrectable !== 1'b1) begin

        $display("ERROR: wrong flags after instantaneous two-bit mask injection");
        $display("  single_error  = %0d", single_error);
        $display("  double_error  = %0d", double_error);
        $display("  uncorrectable = %0d", uncorrectable);
        error_count = error_count + 1;
    end

    if (error_count == 0) begin
        $display("Protected memory model test passed.");
    end else begin
        $display("Protected memory model test failed. Errors: %0d", error_count);
        $fatal(1);
    end

    $finish;
end

endmodule
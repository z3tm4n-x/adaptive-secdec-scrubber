`timescale 1ns/1ps

module tb_secded_decoder;

reg  [38:0] codeword_in;

wire [38:0] codeword_corrected;
wire [31:0] data_out;
wire        single_error;
wire        double_error;
wire        uncorrectable;
wire [5:0]  error_position;

reg  [31:0] data_from_file;
reg  [39:0] expected_from_file;
reg  [38:0] expected_codeword;

reg  [38:0] corrupted_codeword;

integer file;
integer read_count;
integer test_count;
integer error_count;
integer pos;
integer pos_a;
integer pos_b;

secded_32_39_decoder dut (
    .codeword_in(codeword_in),
    .codeword_corrected(codeword_corrected),
    .data_out(data_out),
    .single_error(single_error),
    .double_error(double_error),
    .uncorrectable(uncorrectable),
    .error_position(error_position)
);

task check_no_error;
    begin
        codeword_in = expected_codeword;
        #1;

        if (data_out !== data_from_file) begin
            $display("ERROR no-error data mismatch at test %0d", test_count);
            $display("  expected data = 0x%08h", data_from_file);
            $display("  actual data   = 0x%08h", data_out);
            error_count = error_count + 1;
        end

        if (codeword_corrected !== expected_codeword) begin
            $display("ERROR no-error codeword mismatch at test %0d", test_count);
            error_count = error_count + 1;
        end

        if (single_error !== 1'b0 || double_error !== 1'b0 || uncorrectable !== 1'b0 || error_position !== 6'd0) begin
            $display("ERROR no-error flags mismatch at test %0d", test_count);
            $display("  single_error  = %0d", single_error);
            $display("  double_error  = %0d", double_error);
            $display("  uncorrectable = %0d", uncorrectable);
            $display("  error_position = %0d", error_position);
            error_count = error_count + 1;
        end
    end
endtask

task check_single_error;
    input integer bit_index;
    begin
        corrupted_codeword = expected_codeword ^ (39'd1 << bit_index);
        codeword_in = corrupted_codeword;
        #1;

        if (data_out !== data_from_file) begin
            $display("ERROR single-error data mismatch at test %0d bit %0d", test_count, bit_index);
            $display("  expected data = 0x%08h", data_from_file);
            $display("  actual data   = 0x%08h", data_out);
            error_count = error_count + 1;
        end

        if (codeword_corrected !== expected_codeword) begin
            $display("ERROR single-error correction mismatch at test %0d bit %0d", test_count, bit_index);
            $display("  expected corrected = 0x%010h", expected_codeword);
            $display("  actual corrected   = 0x%010h", codeword_corrected);
            error_count = error_count + 1;
        end

        if (single_error !== 1'b1 || double_error !== 1'b0 || uncorrectable !== 1'b0) begin
            $display("ERROR single-error flags mismatch at test %0d bit %0d", test_count, bit_index);
            $display("  single_error  = %0d", single_error);
            $display("  double_error  = %0d", double_error);
            $display("  uncorrectable = %0d", uncorrectable);
            error_count = error_count + 1;
        end

        if (error_position !== (bit_index + 1)) begin
            $display("ERROR single-error position mismatch at test %0d bit %0d", test_count, bit_index);
            $display("  expected position = %0d", bit_index + 1);
            $display("  actual position   = %0d", error_position);
            error_count = error_count + 1;
        end
    end
endtask

task check_double_error;
    input integer bit_index_a;
    input integer bit_index_b;
    begin
        corrupted_codeword = expected_codeword ^ (39'd1 << bit_index_a) ^ (39'd1 << bit_index_b);
        codeword_in = corrupted_codeword;
        #1;

        if (single_error !== 1'b0 || double_error !== 1'b1 || uncorrectable !== 1'b1) begin
            $display("ERROR double-error flags mismatch at test %0d bits %0d %0d", test_count, bit_index_a, bit_index_b);
            $display("  single_error  = %0d", single_error);
            $display("  double_error  = %0d", double_error);
            $display("  uncorrectable = %0d", uncorrectable);
            error_count = error_count + 1;
        end
    end
endtask

initial begin
    $dumpfile("results/logs/secded_decoder.vcd");
    $dumpvars(0, tb_secded_decoder);

    test_count = 0;
    error_count = 0;

    file = $fopen("tb/secded_encode_vectors.txt", "r");

    if (file == 0) begin
        $display("ERROR: cannot open tb/secded_encode_vectors.txt");
        $fatal(1);
    end

    while (!$feof(file)) begin
        read_count = $fscanf(file, "%h %h\n", data_from_file, expected_from_file);

        if (read_count == 2) begin
            expected_codeword = expected_from_file[38:0];

            /*
             * 1. Проверка без ошибки.
             */
            check_no_error();

            /*
             * 2. Проверка всех одиночных ошибок.
             * bit_index = 0 соответствует позиции 1.
             * bit_index = 38 соответствует позиции 39.
             */
            for (pos = 0; pos < 39; pos = pos + 1) begin
                check_single_error(pos);
            end

            /*
             * 3. Проверка всех двойных ошибок.
             */
            for (pos_a = 0; pos_a < 39; pos_a = pos_a + 1) begin
                for (pos_b = pos_a + 1; pos_b < 39; pos_b = pos_b + 1) begin
                    check_double_error(pos_a, pos_b);
                end
            end

            test_count = test_count + 1;
        end
    end

    $fclose(file);

    if (error_count == 0) begin
        $display("SECDED decoder test passed. Data words: %0d", test_count);
    end else begin
        $display("SECDED decoder test failed. Errors: %0d", error_count);
        $fatal(1);
    end

    $finish;
end

endmodule
`timescale 1ns/1ps

module tb_secded_encoder;

reg  [31:0] data_in;
wire [38:0] codeword_out;

reg  [31:0] data_from_file;
reg  [39:0] expected_from_file;
reg  [38:0] expected_codeword;

integer file;
integer read_count;
integer test_count;
integer error_count;

secded_32_39_encoder dut (
    .data_in(data_in),
    .codeword_out(codeword_out)
);

initial begin
    $dumpfile("results/logs/secded_encoder.vcd");
    $dumpvars(0, tb_secded_encoder);

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
            data_in = data_from_file;
            expected_codeword = expected_from_file[38:0];

            #1;

            if (codeword_out !== expected_codeword) begin
                $display("ERROR at test %0d", test_count);
                $display("  data              = 0x%08h", data_in);
                $display("  expected_codeword = 0x%010h", expected_codeword);
                $display("  actual_codeword   = 0x%010h", codeword_out);
                error_count = error_count + 1;
            end

            test_count = test_count + 1;
        end
    end

    $fclose(file);

    if (error_count == 0) begin
        $display("SECDED encoder test passed. Tests: %0d", test_count);
    end else begin
        $display("SECDED encoder test failed. Errors: %0d", error_count);
        $fatal(1);
    end

    $finish;
end

endmodule
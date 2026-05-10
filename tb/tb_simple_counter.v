`timescale 1ns/1ps

module tb_simple_counter;

reg clk;
reg rst;
wire [3:0] count;

simple_counter dut (
    .clk(clk),
    .rst(rst),
    .count(count)
);

initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
end

initial begin
    $dumpfile("results/logs/simple_counter.vcd");
    $dumpvars(0, tb_simple_counter);

    rst = 1'b1;
    #20;

    rst = 1'b0;
    #200;

    $finish;
end

endmodule
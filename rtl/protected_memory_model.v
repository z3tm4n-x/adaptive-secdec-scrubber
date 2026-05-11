module protected_memory_model #(
    parameter ADDR_WIDTH = 4,
    parameter CODEWORD_WIDTH = 39
)(
    input  wire                         clk,

    input  wire                         read_en,
    input  wire [ADDR_WIDTH-1:0]         read_addr,
    output reg  [CODEWORD_WIDTH-1:0]     read_data,

    input  wire                         write_en,
    input  wire [ADDR_WIDTH-1:0]         write_addr,
    input  wire [CODEWORD_WIDTH-1:0]     write_data,

    /*
     * Одиночная инжекция:
     * инвертируется один бит кодового слова.
     */
    input  wire                         inject_en,
    input  wire [ADDR_WIDTH-1:0]         inject_addr,
    input  wire [5:0]                   inject_bit,

    /*
     * Масочная инжекция:
     * за один такт инвертируются все биты, отмеченные единицами
     * в inject_mask. Этот интерфейс нужен для моделирования
     * мгновенных кластерных событий.
     */
    input  wire                         inject_mask_en,
    input  wire [ADDR_WIDTH-1:0]         inject_mask_addr,
    input  wire [CODEWORD_WIDTH-1:0]     inject_mask
);

localparam DEPTH = (1 << ADDR_WIDTH);

reg [CODEWORD_WIDTH-1:0] memory [0:DEPTH-1];

integer i;

initial begin
    for (i = 0; i < DEPTH; i = i + 1) begin
        memory[i] = {CODEWORD_WIDTH{1'b0}};
    end

    read_data = {CODEWORD_WIDTH{1'b0}};
end

always @(posedge clk) begin
    /*
     * Запись кодового слова.
     */
    if (write_en) begin
        memory[write_addr] <= write_data;
    end

    /*
     * Искусственное внесение одиночной ошибки.
     * inject_bit задаётся в диапазоне 0..38.
     */
    if (inject_en) begin
        if (inject_bit < CODEWORD_WIDTH) begin
            memory[inject_addr][inject_bit] <= ~memory[inject_addr][inject_bit];
        end
    end

    /*
     * Искусственное внесение ошибки по маске.
     * Все единичные биты inject_mask инвертируются в одном кодовом слове
     * за один такт моделирования.
     *
     * Если одновременно активны inject_en и inject_mask_en, результат
     * определяется последовательностью неблокирующих присваиваний.
     * В проверочных стендах эти два режима инжекции должны использоваться
     * раздельно.
     */
    if (inject_mask_en) begin
        memory[inject_mask_addr] <= memory[inject_mask_addr] ^ inject_mask;
    end

    /*
     * Синхронное чтение.
     * read_data обновляется по переднему фронту clk.
     */
    if (read_en) begin
        read_data <= memory[read_addr];
    end
end

endmodule
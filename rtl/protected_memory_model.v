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

reg [CODEWORD_WIDTH-1:0] single_inject_mask;
reg                       single_inject_valid;

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
     * Искусственное внесение ошибок.
     *
     * Одиночная инжекция и масочная инжекция обрабатываются в одной
     * логике, чтобы исключить неоднозначность неблокирующих присваиваний
     * при одновременной активности inject_en и inject_mask_en.
     *
     * Если обе инжекции относятся к одному адресу, маски объединяются.
     * Если адреса разные, обе инжекции выполняются независимо.
     */
    single_inject_mask = {CODEWORD_WIDTH{1'b0}};
    single_inject_valid = 1'b0;

    if (inject_en) begin
        if (inject_bit < CODEWORD_WIDTH) begin
            single_inject_mask[inject_bit] = 1'b1;
            single_inject_valid = 1'b1;
        end
    end

    if (single_inject_valid && inject_mask_en && (inject_addr == inject_mask_addr)) begin
        memory[inject_addr] <= memory[inject_addr] ^ single_inject_mask ^ inject_mask;
    end else begin
        if (single_inject_valid) begin
            memory[inject_addr] <= memory[inject_addr] ^ single_inject_mask;
        end

        if (inject_mask_en) begin
            memory[inject_mask_addr] <= memory[inject_mask_addr] ^ inject_mask;
        end
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
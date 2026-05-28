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
    input  wire [CODEWORD_WIDTH-1:0]     inject_mask,

    /*
     * Дополнительные масочные инжекции для моделирования истинно
     * одновременных кластеров, поражающих несколько кодовых слов
     * за один такт моделирования.
     */
    input  wire                         inject_mask1_en,
    input  wire [ADDR_WIDTH-1:0]         inject_mask1_addr,
    input  wire [CODEWORD_WIDTH-1:0]     inject_mask1,

    input  wire                         inject_mask2_en,
    input  wire [ADDR_WIDTH-1:0]         inject_mask2_addr,
    input  wire [CODEWORD_WIDTH-1:0]     inject_mask2,

    input  wire                         inject_mask3_en,
    input  wire [ADDR_WIDTH-1:0]         inject_mask3_addr,
    input  wire [CODEWORD_WIDTH-1:0]     inject_mask3
);

localparam DEPTH = (1 << ADDR_WIDTH);

reg [CODEWORD_WIDTH-1:0] memory [0:DEPTH-1];

integer i;

reg [CODEWORD_WIDTH-1:0] single_inject_mask;
reg                       single_inject_valid;
reg [CODEWORD_WIDTH-1:0] combined_inject_mask;

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
     * Все активные инжекции текущего такта объединяются по адресу.
     * Это позволяет моделировать одномоментный кластер, который поражает
     * несколько кодовых слов в один такт. Если несколько масок относятся
     * к одному адресу, они объединяются XOR до записи в память.
     */
    single_inject_mask = {CODEWORD_WIDTH{1'b0}};
    single_inject_valid = 1'b0;

    if (inject_en) begin
        if (inject_bit < CODEWORD_WIDTH) begin
            single_inject_mask[inject_bit] = 1'b1;
            single_inject_valid = 1'b1;
        end
    end

    for (i = 0; i < DEPTH; i = i + 1) begin
        combined_inject_mask = {CODEWORD_WIDTH{1'b0}};

        if (single_inject_valid && (inject_addr == i[ADDR_WIDTH-1:0])) begin
            combined_inject_mask = combined_inject_mask ^ single_inject_mask;
        end

        if (inject_mask_en && (inject_mask_addr == i[ADDR_WIDTH-1:0])) begin
            combined_inject_mask = combined_inject_mask ^ inject_mask;
        end

        if (inject_mask1_en && (inject_mask1_addr == i[ADDR_WIDTH-1:0])) begin
            combined_inject_mask = combined_inject_mask ^ inject_mask1;
        end

        if (inject_mask2_en && (inject_mask2_addr == i[ADDR_WIDTH-1:0])) begin
            combined_inject_mask = combined_inject_mask ^ inject_mask2;
        end

        if (inject_mask3_en && (inject_mask3_addr == i[ADDR_WIDTH-1:0])) begin
            combined_inject_mask = combined_inject_mask ^ inject_mask3;
        end

        if (combined_inject_mask != {CODEWORD_WIDTH{1'b0}}) begin
            memory[i] <= memory[i] ^ combined_inject_mask;
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
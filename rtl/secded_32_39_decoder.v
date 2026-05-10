module secded_32_39_decoder (
    input  wire [38:0] codeword_in,

    output reg  [38:0] codeword_corrected,
    output reg  [31:0] data_out,

    output reg         single_error,
    output reg         double_error,
    output reg         uncorrectable,
    output reg  [5:0]  error_position
);

reg [5:0] syndrome;
reg overall_parity_error;
reg parity;
integer pos;

always @* begin
    /*
     * Соответствие:
     * codeword_in[0]  — позиция 1
     * codeword_in[1]  — позиция 2
     * ...
     * codeword_in[38] — позиция 39
     *
     * Проверочные позиции Хэмминга:
     * 1, 2, 4, 8, 16, 32.
     *
     * Общий бит чётности:
     * позиция 39.
     */

    syndrome = 6'd0;

    /*
     * Вычисление синдрома.
     * Для каждой проверочной позиции вычисляется чётность
     * соответствующей группы позиций 1..38.
     */

    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if ((pos & 1) != 0)
            parity = parity ^ codeword_in[pos - 1];
    end
    if (parity)
        syndrome = syndrome | 6'd1;

    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if ((pos & 2) != 0)
            parity = parity ^ codeword_in[pos - 1];
    end
    if (parity)
        syndrome = syndrome | 6'd2;

    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if ((pos & 4) != 0)
            parity = parity ^ codeword_in[pos - 1];
    end
    if (parity)
        syndrome = syndrome | 6'd4;

    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if ((pos & 8) != 0)
            parity = parity ^ codeword_in[pos - 1];
    end
    if (parity)
        syndrome = syndrome | 6'd8;

    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if ((pos & 16) != 0)
            parity = parity ^ codeword_in[pos - 1];
    end
    if (parity)
        syndrome = syndrome | 6'd16;

    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if ((pos & 32) != 0)
            parity = parity ^ codeword_in[pos - 1];
    end
    if (parity)
        syndrome = syndrome | 6'd32;

    /*
     * Общая чётность всего 39-битного кодового слова.
     * Если результат равен 1, значит общая чётность нарушена.
     */
    overall_parity_error = ^codeword_in;

    /*
     * Значения по умолчанию.
     */
    codeword_corrected = codeword_in;
    single_error = 1'b0;
    double_error = 1'b0;
    uncorrectable = 1'b0;
    error_position = 6'd0;

    /*
     * Разбор четырёх случаев SECDED.
     */

    if ((syndrome == 6'd0) && (overall_parity_error == 1'b0)) begin
        /*
         * Ошибки нет.
         */
        codeword_corrected = codeword_in;
        single_error = 1'b0;
        double_error = 1'b0;
        uncorrectable = 1'b0;
        error_position = 6'd0;
    end

    else if ((syndrome != 6'd0) && (overall_parity_error == 1'b1)) begin
        /*
         * Одиночная ошибка в одной из позиций 1..38.
         */
        if (syndrome <= 6'd38) begin
            codeword_corrected = codeword_in ^ (39'd1 << (syndrome - 6'd1));
            single_error = 1'b1;
            double_error = 1'b0;
            uncorrectable = 1'b0;
            error_position = syndrome;
        end else begin
            /*
             * Для данной структуры кода такой случай не должен возникать
             * при одиночной ошибке. Оставляем его как защитную ветвь.
             */
            codeword_corrected = codeword_in;
            single_error = 1'b0;
            double_error = 1'b0;
            uncorrectable = 1'b1;
            error_position = 6'd0;
        end
    end

    else if ((syndrome == 6'd0) && (overall_parity_error == 1'b1)) begin
        /*
         * Одиночная ошибка в общем бите чётности, позиция 39.
         */
        codeword_corrected = codeword_in ^ (39'd1 << 38);
        single_error = 1'b1;
        double_error = 1'b0;
        uncorrectable = 1'b0;
        error_position = 6'd39;
    end

    else begin
        /*
         * syndrome != 0, overall_parity_error == 0.
         * Двойная ошибка: обнаруживается, но не исправляется.
         */
        codeword_corrected = codeword_in;
        single_error = 1'b0;
        double_error = 1'b1;
        uncorrectable = 1'b1;
        error_position = 6'd0;
    end

    /*
     * Извлечение информационных битов из исправленного кодового слова.
     */
    data_out[0]  = codeword_corrected[2];   /* позиция 3  */
    data_out[1]  = codeword_corrected[4];   /* позиция 5  */
    data_out[2]  = codeword_corrected[5];   /* позиция 6  */
    data_out[3]  = codeword_corrected[6];   /* позиция 7  */
    data_out[4]  = codeword_corrected[8];   /* позиция 9  */
    data_out[5]  = codeword_corrected[9];   /* позиция 10 */
    data_out[6]  = codeword_corrected[10];  /* позиция 11 */
    data_out[7]  = codeword_corrected[11];  /* позиция 12 */

    data_out[8]  = codeword_corrected[12];  /* позиция 13 */
    data_out[9]  = codeword_corrected[13];  /* позиция 14 */
    data_out[10] = codeword_corrected[14];  /* позиция 15 */
    data_out[11] = codeword_corrected[16];  /* позиция 17 */
    data_out[12] = codeword_corrected[17];  /* позиция 18 */
    data_out[13] = codeword_corrected[18];  /* позиция 19 */
    data_out[14] = codeword_corrected[19];  /* позиция 20 */
    data_out[15] = codeword_corrected[20];  /* позиция 21 */

    data_out[16] = codeword_corrected[21];  /* позиция 22 */
    data_out[17] = codeword_corrected[22];  /* позиция 23 */
    data_out[18] = codeword_corrected[23];  /* позиция 24 */
    data_out[19] = codeword_corrected[24];  /* позиция 25 */
    data_out[20] = codeword_corrected[25];  /* позиция 26 */
    data_out[21] = codeword_corrected[26];  /* позиция 27 */
    data_out[22] = codeword_corrected[27];  /* позиция 28 */
    data_out[23] = codeword_corrected[28];  /* позиция 29 */

    data_out[24] = codeword_corrected[29];  /* позиция 30 */
    data_out[25] = codeword_corrected[30];  /* позиция 31 */
    data_out[26] = codeword_corrected[32];  /* позиция 33 */
    data_out[27] = codeword_corrected[33];  /* позиция 34 */
    data_out[28] = codeword_corrected[34];  /* позиция 35 */
    data_out[29] = codeword_corrected[35];  /* позиция 36 */
    data_out[30] = codeword_corrected[36];  /* позиция 37 */
    data_out[31] = codeword_corrected[37];  /* позиция 38 */
end

endmodule
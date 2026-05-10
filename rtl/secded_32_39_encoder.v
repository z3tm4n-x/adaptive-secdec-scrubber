module secded_32_39_encoder (
    input  wire [31:0] data_in,
    output reg  [38:0] codeword_out
);

reg [38:0] cw;
reg parity;
integer pos;

always @* begin
    cw = 39'd0;

    /*
     * Соответствие:
     * codeword_out[0]  — позиция 1
     * codeword_out[1]  — позиция 2
     * ...
     * codeword_out[38] — позиция 39
     *
     * Проверочные позиции Хэмминга:
     * 1, 2, 4, 8, 16, 32.
     *
     * Общий бит чётности:
     * позиция 39.
     */

    /* Размещение 32 информационных битов. */
    cw[2]  = data_in[0];   /* позиция 3  */
    cw[4]  = data_in[1];   /* позиция 5  */
    cw[5]  = data_in[2];   /* позиция 6  */
    cw[6]  = data_in[3];   /* позиция 7  */
    cw[8]  = data_in[4];   /* позиция 9  */
    cw[9]  = data_in[5];   /* позиция 10 */
    cw[10] = data_in[6];   /* позиция 11 */
    cw[11] = data_in[7];   /* позиция 12 */

    cw[12] = data_in[8];   /* позиция 13 */
    cw[13] = data_in[9];   /* позиция 14 */
    cw[14] = data_in[10];  /* позиция 15 */
    cw[16] = data_in[11];  /* позиция 17 */
    cw[17] = data_in[12];  /* позиция 18 */
    cw[18] = data_in[13];  /* позиция 19 */
    cw[19] = data_in[14];  /* позиция 20 */
    cw[20] = data_in[15];  /* позиция 21 */

    cw[21] = data_in[16];  /* позиция 22 */
    cw[22] = data_in[17];  /* позиция 23 */
    cw[23] = data_in[18];  /* позиция 24 */
    cw[24] = data_in[19];  /* позиция 25 */
    cw[25] = data_in[20];  /* позиция 26 */
    cw[26] = data_in[21];  /* позиция 27 */
    cw[27] = data_in[22];  /* позиция 28 */
    cw[28] = data_in[23];  /* позиция 29 */

    cw[29] = data_in[24];  /* позиция 30 */
    cw[30] = data_in[25];  /* позиция 31 */
    cw[32] = data_in[26];  /* позиция 33 */
    cw[33] = data_in[27];  /* позиция 34 */
    cw[34] = data_in[28];  /* позиция 35 */
    cw[35] = data_in[29];  /* позиция 36 */
    cw[36] = data_in[30];  /* позиция 37 */
    cw[37] = data_in[31];  /* позиция 38 */

    /*
     * Проверочный бит позиции 1.
     * Учитываются позиции, у которых в двоичном номере установлен бит 1.
     */
    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if (((pos & 1) != 0) && (pos != 1))
            parity = parity ^ cw[pos - 1];
    end
    cw[0] = parity;

    /* Проверочный бит позиции 2. */
    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if (((pos & 2) != 0) && (pos != 2))
            parity = parity ^ cw[pos - 1];
    end
    cw[1] = parity;

    /* Проверочный бит позиции 4. */
    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if (((pos & 4) != 0) && (pos != 4))
            parity = parity ^ cw[pos - 1];
    end
    cw[3] = parity;

    /* Проверочный бит позиции 8. */
    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if (((pos & 8) != 0) && (pos != 8))
            parity = parity ^ cw[pos - 1];
    end
    cw[7] = parity;

    /* Проверочный бит позиции 16. */
    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if (((pos & 16) != 0) && (pos != 16))
            parity = parity ^ cw[pos - 1];
    end
    cw[15] = parity;

    /* Проверочный бит позиции 32. */
    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        if (((pos & 32) != 0) && (pos != 32))
            parity = parity ^ cw[pos - 1];
    end
    cw[31] = parity;

    /*
     * Общий бит чётности.
     * Он выбирается так, чтобы всё 39-битное слово имело чётную чётность.
     */
    parity = 1'b0;
    for (pos = 1; pos <= 38; pos = pos + 1) begin
        parity = parity ^ cw[pos - 1];
    end
    cw[38] = parity;

    codeword_out = cw;
end

endmodule
module fixed_scrub_controller #(
    parameter ADDR_WIDTH = 4,
    parameter CODEWORD_WIDTH = 39,
    parameter INTERVAL_CYCLES = 20
)(
    input  wire                         clk,
    input  wire                         rst,
    input  wire                         enable,

    output wire                         mem_read_en,
    output wire [ADDR_WIDTH-1:0]         mem_read_addr,
    input  wire [CODEWORD_WIDTH-1:0]     mem_read_data,

    output wire                         mem_write_en,
    output wire [ADDR_WIDTH-1:0]         mem_write_addr,
    output wire [CODEWORD_WIDTH-1:0]     mem_write_data,

    output reg                          scrub_active,
    output reg  [31:0]                  scrub_cycle_count,
    output reg  [31:0]                  memory_read_count,
    output reg  [31:0]                  memory_write_count,
    output reg  [31:0]                  corrected_error_count,
    output reg  [31:0]                  uncorrectable_error_count
);

localparam DEPTH = (1 << ADDR_WIDTH);

localparam STATE_WAIT      = 3'd0;
localparam STATE_READ_REQ  = 3'd1;
localparam STATE_READ_WAIT = 3'd2;
localparam STATE_DECODE    = 3'd3;
localparam STATE_WRITE     = 3'd4;
localparam STATE_NEXT      = 3'd5;
localparam STATE_DONE      = 3'd6;

reg [2:0] state;
reg [31:0] interval_counter;
reg [ADDR_WIDTH-1:0] current_addr;

wire [38:0] decoder_corrected_codeword;
wire [31:0] decoder_data_out;
wire        decoder_single_error;
wire        decoder_double_error;
wire        decoder_uncorrectable;
wire [5:0]  decoder_error_position;

secded_32_39_decoder decoder_inst (
    .codeword_in(mem_read_data[38:0]),
    .codeword_corrected(decoder_corrected_codeword),
    .data_out(decoder_data_out),
    .single_error(decoder_single_error),
    .double_error(decoder_double_error),
    .uncorrectable(decoder_uncorrectable),
    .error_position(decoder_error_position)
);

/*
 * Управляющие сигналы памяти.
 * Чтение активно только в состоянии READ_REQ.
 * Запись активна только в состоянии WRITE.
 */
assign mem_read_en = (state == STATE_READ_REQ);
assign mem_read_addr = current_addr;

assign mem_write_en = (state == STATE_WRITE);
assign mem_write_addr = current_addr;
assign mem_write_data = decoder_corrected_codeword;

always @(posedge clk) begin
    if (rst) begin
        state <= STATE_WAIT;
        interval_counter <= 32'd0;
        current_addr <= {ADDR_WIDTH{1'b0}};

        scrub_active <= 1'b0;
        scrub_cycle_count <= 32'd0;
        memory_read_count <= 32'd0;
        memory_write_count <= 32'd0;
        corrected_error_count <= 32'd0;
        uncorrectable_error_count <= 32'd0;
    end else begin
        case (state)

            STATE_WAIT: begin
                scrub_active <= 1'b0;
                current_addr <= {ADDR_WIDTH{1'b0}};

                if (!enable) begin
                    interval_counter <= 32'd0;
                end else begin
                    if (interval_counter >= (INTERVAL_CYCLES - 1)) begin
                        interval_counter <= 32'd0;
                        scrub_active <= 1'b1;
                        state <= STATE_READ_REQ;
                    end else begin
                        interval_counter <= interval_counter + 32'd1;
                    end
                end
            end

            STATE_READ_REQ: begin
                scrub_active <= 1'b1;
                memory_read_count <= memory_read_count + 32'd1;
                state <= STATE_READ_WAIT;
            end

            STATE_READ_WAIT: begin
                scrub_active <= 1'b1;
                state <= STATE_DECODE;
            end

            STATE_DECODE: begin
                scrub_active <= 1'b1;

                if (decoder_single_error) begin
                    corrected_error_count <= corrected_error_count + 32'd1;
                    state <= STATE_WRITE;
                end else begin
                    if (decoder_uncorrectable) begin
                        uncorrectable_error_count <= uncorrectable_error_count + 32'd1;
                    end

                    state <= STATE_NEXT;
                end
            end

            STATE_WRITE: begin
                scrub_active <= 1'b1;
                memory_write_count <= memory_write_count + 32'd1;
                state <= STATE_NEXT;
            end

            STATE_NEXT: begin
                scrub_active <= 1'b1;

                if (current_addr == (DEPTH - 1)) begin
                    state <= STATE_DONE;
                end else begin
                    current_addr <= current_addr + {{(ADDR_WIDTH-1){1'b0}}, 1'b1};
                    state <= STATE_READ_REQ;
                end
            end

            STATE_DONE: begin
                scrub_active <= 1'b0;
                scrub_cycle_count <= scrub_cycle_count + 32'd1;
                current_addr <= {ADDR_WIDTH{1'b0}};
                state <= STATE_WAIT;
            end

            default: begin
                state <= STATE_WAIT;
            end

        endcase
    end
end

endmodule
module adaptive_scrub_controller #(
    parameter ADDR_WIDTH = 4,
    parameter CODEWORD_WIDTH = 39,
    parameter LEVEL_WIDTH = 3,
    parameter INTERVAL_WIDTH = 32
)(
    input  wire                         clk,
    input  wire                         rst,
    input  wire                         enable,

    input  wire [1:0]                   mode,

    input  wire [LEVEL_WIDTH-1:0]        ctrl_level,
    input  wire                         ctrl_valid,
    input  wire                         ctrl_update,

    input  wire [INTERVAL_WIDTH-1:0]     fixed_interval,
    input  wire [INTERVAL_WIDTH-1:0]     safe_interval,
    input  wire [31:0]                  max_control_age,

    input  wire [INTERVAL_WIDTH-1:0]     level0_interval,
    input  wire [INTERVAL_WIDTH-1:0]     level1_interval,
    input  wire [INTERVAL_WIDTH-1:0]     level2_interval,
    input  wire [INTERVAL_WIDTH-1:0]     level3_interval,
    input  wire [INTERVAL_WIDTH-1:0]     level4_interval,
    input  wire [INTERVAL_WIDTH-1:0]     level5_interval,
    input  wire [INTERVAL_WIDTH-1:0]     level6_interval,
    input  wire [INTERVAL_WIDTH-1:0]     level7_interval,

    input  wire [LEVEL_WIDTH-1:0]        threshold_low_to_medium,
    input  wire [LEVEL_WIDTH-1:0]        threshold_medium_to_low,
    input  wire [LEVEL_WIDTH-1:0]        threshold_medium_to_high,
    input  wire [LEVEL_WIDTH-1:0]        threshold_high_to_medium,

    input  wire [INTERVAL_WIDTH-1:0]     threshold_low_interval,
    input  wire [INTERVAL_WIDTH-1:0]     threshold_medium_interval,
    input  wire [INTERVAL_WIDTH-1:0]     threshold_high_interval,

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
    output reg  [31:0]                  uncorrectable_error_count,
    output reg  [31:0]                  interval_switch_count,

    output wire [INTERVAL_WIDTH-1:0]     selected_interval,
    output wire                         safe_mode_active,
    output wire [LEVEL_WIDTH-1:0]        current_level,
    output wire [1:0]                   threshold_state,
    output wire [31:0]                  control_age
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

reg [INTERVAL_WIDTH-1:0] previous_selected_interval;
reg interval_initialized;

wire [INTERVAL_WIDTH-1:0] effective_interval;

assign effective_interval =
    (selected_interval == {INTERVAL_WIDTH{1'b0}})
        ? {{(INTERVAL_WIDTH-1){1'b0}}, 1'b1}
        : selected_interval;

wire [38:0] decoder_corrected_codeword;
wire [31:0] decoder_data_out;
wire        decoder_single_error;
wire        decoder_double_error;
wire        decoder_uncorrectable;
wire [5:0]  decoder_error_position;

interval_selector #(
    .LEVEL_WIDTH(LEVEL_WIDTH),
    .INTERVAL_WIDTH(INTERVAL_WIDTH)
) interval_selector_inst (
    .clk(clk),
    .rst(rst),
    .enable(enable),

    .mode(mode),

    .ctrl_level(ctrl_level),
    .ctrl_valid(ctrl_valid),
    .ctrl_update(ctrl_update),

    .fixed_interval(fixed_interval),
    .safe_interval(safe_interval),
    .max_control_age(max_control_age),

    .level0_interval(level0_interval),
    .level1_interval(level1_interval),
    .level2_interval(level2_interval),
    .level3_interval(level3_interval),
    .level4_interval(level4_interval),
    .level5_interval(level5_interval),
    .level6_interval(level6_interval),
    .level7_interval(level7_interval),

    .threshold_low_to_medium(threshold_low_to_medium),
    .threshold_medium_to_low(threshold_medium_to_low),
    .threshold_medium_to_high(threshold_medium_to_high),
    .threshold_high_to_medium(threshold_high_to_medium),

    .threshold_low_interval(threshold_low_interval),
    .threshold_medium_interval(threshold_medium_interval),
    .threshold_high_interval(threshold_high_interval),

    .selected_interval(selected_interval),
    .safe_mode_active(safe_mode_active),
    .current_level(current_level),
    .threshold_state(threshold_state),
    .control_age(control_age)
);

secded_32_39_decoder decoder_inst (
    .codeword_in(mem_read_data[38:0]),
    .codeword_corrected(decoder_corrected_codeword),
    .data_out(decoder_data_out),
    .single_error(decoder_single_error),
    .double_error(decoder_double_error),
    .uncorrectable(decoder_uncorrectable),
    .error_position(decoder_error_position)
);

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
        interval_switch_count <= 32'd0;

        previous_selected_interval <= {INTERVAL_WIDTH{1'b0}};
        interval_initialized <= 1'b0;
    end else begin

        /*
         * Отдельно считаем переключения выбранного интервала.
         */
        if (enable) begin
            if (!interval_initialized) begin
                previous_selected_interval <= selected_interval;
                interval_initialized <= 1'b1;
            end else begin
                if (selected_interval != previous_selected_interval) begin
                    interval_switch_count <= interval_switch_count + 32'd1;
                    previous_selected_interval <= selected_interval;
                end
            end
        end

        case (state)

            STATE_WAIT: begin
                scrub_active <= 1'b0;
                current_addr <= {ADDR_WIDTH{1'b0}};

                if (!enable) begin
                    interval_counter <= 32'd0;
                end else begin
                    if ((interval_counter + 32'd1) >= effective_interval[31:0]) begin
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
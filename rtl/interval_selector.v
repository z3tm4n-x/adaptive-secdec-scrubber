module interval_selector #(
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

    output reg  [INTERVAL_WIDTH-1:0]     selected_interval,
    output reg                          safe_mode_active,
    output reg  [LEVEL_WIDTH-1:0]        current_level,
    output reg  [1:0]                   threshold_state,
    output reg  [31:0]                  control_age
);

localparam MODE_FIXED     = 2'd0;
localparam MODE_TABLE     = 2'd1;
localparam MODE_THRESHOLD = 2'd2;

localparam THRESHOLD_LOW    = 2'd0;
localparam THRESHOLD_MEDIUM = 2'd1;
localparam THRESHOLD_HIGH   = 2'd2;

always @(posedge clk) begin
    if (rst) begin
        current_level <= {LEVEL_WIDTH{1'b0}};
        threshold_state <= THRESHOLD_LOW;
        control_age <= 32'd0;
        safe_mode_active <= 1'b0;
    end else begin
        if (!enable) begin
            current_level <= {LEVEL_WIDTH{1'b0}};
            threshold_state <= THRESHOLD_LOW;
            control_age <= 32'd0;
            safe_mode_active <= 1'b0;
        end else begin
            if (ctrl_update && ctrl_valid) begin
                current_level <= ctrl_level;
                control_age <= 32'd0;
                safe_mode_active <= 1'b0;

                /*
                 * Обновление состояния пороговой стратегии.
                 * Используется гистерезис:
                 * - переход вверх выполняется по верхнему порогу;
                 * - переход вниз выполняется по нижнему порогу.
                 */
                case (threshold_state)
                    THRESHOLD_LOW: begin
                        if (ctrl_level >= threshold_low_to_medium)
                            threshold_state <= THRESHOLD_MEDIUM;
                        else
                            threshold_state <= THRESHOLD_LOW;
                    end

                    THRESHOLD_MEDIUM: begin
                        if (ctrl_level >= threshold_medium_to_high)
                            threshold_state <= THRESHOLD_HIGH;
                        else if (ctrl_level <= threshold_medium_to_low)
                            threshold_state <= THRESHOLD_LOW;
                        else
                            threshold_state <= THRESHOLD_MEDIUM;
                    end

                    THRESHOLD_HIGH: begin
                        if (ctrl_level <= threshold_high_to_medium)
                            threshold_state <= THRESHOLD_MEDIUM;
                        else
                            threshold_state <= THRESHOLD_HIGH;
                    end

                    default: begin
                        threshold_state <= THRESHOLD_LOW;
                    end
                endcase
            end else begin
                if (control_age != 32'hFFFF_FFFF)
                    control_age <= control_age + 32'd1;

                if (control_age >= max_control_age)
                    safe_mode_active <= 1'b1;
            end
        end
    end
end

always @* begin
    if (safe_mode_active) begin
        selected_interval = safe_interval;
    end else begin
        case (mode)
            MODE_FIXED: begin
                selected_interval = fixed_interval;
            end

            MODE_TABLE: begin
                case (current_level)
                    3'd0: selected_interval = level0_interval;
                    3'd1: selected_interval = level1_interval;
                    3'd2: selected_interval = level2_interval;
                    3'd3: selected_interval = level3_interval;
                    3'd4: selected_interval = level4_interval;
                    3'd5: selected_interval = level5_interval;
                    3'd6: selected_interval = level6_interval;
                    3'd7: selected_interval = level7_interval;
                    default: selected_interval = safe_interval;
                endcase
            end

            MODE_THRESHOLD: begin
                case (threshold_state)
                    THRESHOLD_LOW:    selected_interval = threshold_low_interval;
                    THRESHOLD_MEDIUM: selected_interval = threshold_medium_interval;
                    THRESHOLD_HIGH:   selected_interval = threshold_high_interval;
                    default:          selected_interval = safe_interval;
                endcase
            end

            default: begin
                selected_interval = safe_interval;
            end
        endcase
    end
end

endmodule
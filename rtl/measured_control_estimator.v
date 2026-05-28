module measured_control_estimator #(
    parameter LEVEL_WIDTH = 3,
    parameter COUNTER_WIDTH = 32,
    parameter SCORE_WIDTH = 32,

    /*
     * Window length in model cycles.
     *
     * For dissertation experiments this is normally 25000 cycles.
     * The testbench overrides it with a small value.
     */
    parameter WINDOW_CYCLES = 25000,

    /*
     * Integer form of the selected measured-control score.
     *
     * Offline calibration used:
     *   score = corrected_per_100k + 0.5 * DED_per_100k
     *
     * For a 25000-cycle window this is proportional to:
     *   raw_score = 2 * corrected_delta + uncorrectable_delta
     */
    parameter CORRECTED_WEIGHT = 2,
    parameter UNCORRECTABLE_WEIGHT = 1,

    /*
     * Thresholds for raw_score -> level.
     *
     * They implement:
     *   level = round(raw_score / 100 * 7)
     * with saturation to 0..7.
     */
    parameter THRESHOLD_LEVEL1 = 8,
    parameter THRESHOLD_LEVEL2 = 22,
    parameter THRESHOLD_LEVEL3 = 36,
    parameter THRESHOLD_LEVEL4 = 50,
    parameter THRESHOLD_LEVEL5 = 65,
    parameter THRESHOLD_LEVEL6 = 79,
    parameter THRESHOLD_LEVEL7 = 93,

    parameter INITIAL_LEVEL = 0
)(
    input  wire                         clk,
    input  wire                         rst,
    input  wire                         enable,

    input  wire [COUNTER_WIDTH-1:0]     corrected_error_count,
    input  wire [COUNTER_WIDTH-1:0]     uncorrectable_error_count,

    output reg  [LEVEL_WIDTH-1:0]       measured_ctrl_level,
    output reg                          measured_ctrl_valid,
    output reg                          measured_ctrl_update,

    output reg  [31:0]                  measured_window_count,
    output reg  [COUNTER_WIDTH-1:0]     measured_corrected_delta,
    output reg  [COUNTER_WIDTH-1:0]     measured_uncorrectable_delta,
    output reg  [SCORE_WIDTH-1:0]       measured_raw_score
);

reg [COUNTER_WIDTH-1:0] previous_corrected_error_count;
reg [COUNTER_WIDTH-1:0] previous_uncorrectable_error_count;

wire [COUNTER_WIDTH-1:0] corrected_delta_wire;
wire [COUNTER_WIDTH-1:0] uncorrectable_delta_wire;

wire [63:0] corrected_score_wide;
wire [63:0] uncorrectable_score_wide;
wire [63:0] raw_score_wide;

wire [SCORE_WIDTH-1:0] raw_score_saturated;

assign corrected_delta_wire =
    corrected_error_count - previous_corrected_error_count;

assign uncorrectable_delta_wire =
    uncorrectable_error_count - previous_uncorrectable_error_count;

assign corrected_score_wide =
    corrected_delta_wire * CORRECTED_WEIGHT;

assign uncorrectable_score_wide =
    uncorrectable_delta_wire * UNCORRECTABLE_WEIGHT;

assign raw_score_wide =
    corrected_score_wide + uncorrectable_score_wide;

assign raw_score_saturated =
    (raw_score_wide > {SCORE_WIDTH{1'b1}})
        ? {SCORE_WIDTH{1'b1}}
        : raw_score_wide[SCORE_WIDTH-1:0];

function [LEVEL_WIDTH-1:0] score_to_level;
    input [SCORE_WIDTH-1:0] score;
    begin
        if (score >= THRESHOLD_LEVEL7[SCORE_WIDTH-1:0]) begin
            score_to_level = 3'd7;
        end else if (score >= THRESHOLD_LEVEL6[SCORE_WIDTH-1:0]) begin
            score_to_level = 3'd6;
        end else if (score >= THRESHOLD_LEVEL5[SCORE_WIDTH-1:0]) begin
            score_to_level = 3'd5;
        end else if (score >= THRESHOLD_LEVEL4[SCORE_WIDTH-1:0]) begin
            score_to_level = 3'd4;
        end else if (score >= THRESHOLD_LEVEL3[SCORE_WIDTH-1:0]) begin
            score_to_level = 3'd3;
        end else if (score >= THRESHOLD_LEVEL2[SCORE_WIDTH-1:0]) begin
            score_to_level = 3'd2;
        end else if (score >= THRESHOLD_LEVEL1[SCORE_WIDTH-1:0]) begin
            score_to_level = 3'd1;
        end else begin
            score_to_level = {LEVEL_WIDTH{1'b0}};
        end
    end
endfunction

always @(posedge clk) begin
    if (rst) begin
        previous_corrected_error_count <= {COUNTER_WIDTH{1'b0}};
        previous_uncorrectable_error_count <= {COUNTER_WIDTH{1'b0}};

        measured_ctrl_level <= INITIAL_LEVEL[LEVEL_WIDTH-1:0];
        measured_ctrl_valid <= 1'b0;
        measured_ctrl_update <= 1'b0;

        measured_window_count <= 32'd0;
        measured_corrected_delta <= {COUNTER_WIDTH{1'b0}};
        measured_uncorrectable_delta <= {COUNTER_WIDTH{1'b0}};
        measured_raw_score <= {SCORE_WIDTH{1'b0}};
    end else begin
        measured_ctrl_update <= 1'b0;

        if (enable) begin
            if ((measured_window_count + 32'd1) >= WINDOW_CYCLES[31:0]) begin
                measured_window_count <= 32'd0;

                measured_corrected_delta <= corrected_delta_wire;
                measured_uncorrectable_delta <= uncorrectable_delta_wire;
                measured_raw_score <= raw_score_saturated;

                measured_ctrl_level <= score_to_level(raw_score_saturated);
                measured_ctrl_valid <= 1'b1;
                measured_ctrl_update <= 1'b1;

                previous_corrected_error_count <= corrected_error_count;
                previous_uncorrectable_error_count <= uncorrectable_error_count;
            end else begin
                measured_window_count <= measured_window_count + 32'd1;
            end
        end
    end
end

endmodule

// Section 3.4. Packet identity is the absolute basal calendar number.
// Pulses cut and install describe edges entered, not edges just left.
module native64_rule (
    input wire clk, cold, scan_start, common_end, cut, install,
    input wire [35:0] epoch,
    input wire packet, packet_complete,
    input wire [35:0] packet_epoch,
    input wire [15:0] packet_count,
    input wire sealed, scan_bad, loss,
    input wire [15:0] actual_count,
    output reg [3:0] issued,
    output reg [9:0] quiet,
    output reg accepted_zero, command_strobe,
    output wire history_fault
);
    (* DONT_TOUCH = "TRUE" *) reg [9:0] quiet_inv;
    reg [3:0] proposed;
    reg proposed_parity;
    reg received, invalid, closed, initialized, spoiled;
    reg [15:0] stored_count;
    assign history_fault = quiet != ~quiet_inv;
    wire qualified = packet_complete && packet_epoch == epoch && sealed &&
                     !scan_bad && packet_count == actual_count;
    wire conflict = packet && (!qualified || (received && packet_count != stored_count));
    wire has_report = received || (packet && qualified);
    wire dirty_report = (packet && qualified && packet_count != 0);
    wire reject_now = loss || scan_bad || conflict || history_fault || dirty_report;
    wire good_zero = has_report && sealed && !invalid && !reject_now &&
                     actual_count == 0 && (!received || stored_count == 0);
    wire [9:0] advanced = quiet < 596 ? quiet + 10'd1 : 10'd596;
    wire [9:0] following = (initialized && !spoiled) ? advanced : 10'd0;

    function automatic [3:0] level(input [9:0] z);
        if      (z >= 596) level = 9;
        else if (z >= 298) level = 8;
        else if (z >= 149) level = 7;
        else if (z >= 75)  level = 6;
        else if (z >= 38)  level = 5;
        else if (z >= 19)  level = 4;
        else if (z >= 10)  level = 3;
        else if (z >= 5)   level = 2;
        else if (z >= 3)   level = 1;
        else               level = 0;
    endfunction
    wire [3:0] decision = !good_zero ? 4'd0 : common_end ? level(following) :
                           spoiled ? 4'd0 : issued;
    always @(posedge clk) begin
        if (cold) begin
            issued <= 0; quiet <= 0; quiet_inv <= 10'h3ff; proposed <= 0;
            proposed_parity <= 0; received <= 0; invalid <= 0; closed <= 0;
            initialized <= 0; spoiled <= 0; stored_count <= 0;
            accepted_zero <= 0; command_strobe <= 0;
        end else begin
            command_strobe <= install;
            accepted_zero <= 0;
            if (scan_start) begin
                received <= 0; invalid <= 0; closed <= 0; stored_count <= 0;
                proposed <= 0; proposed_parity <= 0;
            end
            if (packet && !closed && !scan_start && qualified && !received) begin
                received <= 1; stored_count <= packet_count;
            end
            // A later packet cannot repair a cut already missed.
            if (reject_now) begin
                invalid <= 1; spoiled <= 1; quiet <= 0; quiet_inv <= 10'h3ff;
            end
            if (cut) begin
                closed <= 1; proposed <= decision; proposed_parity <= ^decision;
                accepted_zero <= good_zero;
                if (!good_zero || common_end) begin
                    quiet <= good_zero ? following : 10'd0;
                    quiet_inv <= good_zero ? ~following : 10'h3ff;
                    spoiled <= !common_end;
                end
                if (!good_zero) invalid <= 1;
                if (common_end) initialized <= 1;
            end
            if (install) begin
                if (closed && !reject_now && !invalid && proposed <= 9 &&
                    proposed_parity == ^proposed) issued <= proposed;
                else begin
                    issued <= 0; quiet <= 0; quiet_inv <= 10'h3ff;
                    if (!common_end || loss || history_fault) spoiled <= 1;
                end
            end
        end
    end
endmodule

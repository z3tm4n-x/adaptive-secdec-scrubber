// Fixed 64 KiB external address calendar. All pin controls are registered.
// Cold is a commissioning input, asserted only before the first modeled read.
module native64_core (
    input wire clk, cold, loss,
    input wire err_in,
    input wire [15:0] dq_in,
    input wire app_request, input wire [14:0] app_address,
    output reg app_grant, app_valid, output reg [15:0] app_data,
    (* DONT_TOUCH="TRUE", IOB="FALSE" *) output reg [14:0] address,
    output wire select_n, oe_n, we_n,
    output reg drive,
    (* IOB="TRUE", DONT_TOUCH="TRUE" *) output reg [14:0] pad_address,
    (* IOB="TRUE", DONT_TOUCH="TRUE" *) output reg pad_select_n, pad_oe_n, pad_we_n,
    (* IOB = "TRUE" *) output reg [15:0] dq_out,
    output reg [15:0] repair_image,
    (* IOB="TRUE", DONT_TOUCH="TRUE" *) output reg [15:0] pad_t_n,
    output reg protect_owner,
    output wire [3:0] issued,
    output wire [9:0] quiet,
    output reg sealed, report_send, output reg [15:0] count,
    output reg [35:0] epoch,
    output wire accepted_zero, command_strobe,
    output reg execution_fault
);
    reg running, active;
    (* DONT_TOUCH="TRUE", IOB="FALSE" *) reg selected, reading, writing;
    assign select_n=!selected; assign oe_n=!reading; assign we_n=!writing;
    (* DONT_TOUCH="TRUE" *) reg [7:0] phase_a, phase_inv;
    (* DONT_TOUCH="TRUE" *) reg phase_parity;
    wire phase_error = (phase_a != ~phase_inv) || (phase_parity != ^phase_a);
    wire [7:0] phase = (phase_parity == ^phase_a) ? phase_a : ~phase_inv;
    reg [12:0] frame;
    reg [9:0] wait_rounds;
    reg wait_parity;
    reg installed;
    wire [3:0] policy_level;
    // The current scan starts with FAST prearmed. An older slow command
    // may not authorize skips if this scan's installation pulse is lost.
    assign issued=(installed || command_strobe) ? policy_level : 4'd0;
    wire wrap_frame = phase == 139;
    wire wrap_round = wrap_frame && (&frame);
    wire wait_ok = wait_parity == ^wait_rounds;
    wire next_active = active ? issued == 0 : (wait_rounds <= 1 || !wait_ok);
    wire [9:0] reload_wait = (10'd1 << issued) - 1'b1;
    wire [9:0] next_wait = active ? reload_wait :
                           (wait_rounds == 0 || !wait_ok ? 10'd0 : wait_rounds - 1'b1);
    wire scan_start = !running || (wrap_round && next_active);
    wire common_end = epoch[8:0] == 0;
    wire cut = active && (&frame) && phase == 109;
    wire install = active && (&frame) && phase == 129;
    wire new_frame = !running || wrap_frame;
    wire [7:0] next_phase = new_frame ? 8'd0 : phase+1'b1;
    wire start_visit = (new_frame && (!running || (wrap_round ? next_active : active))) ||
                       (active && (phase == 23 || phase == 51 || phase == 75));
    wire [1:0] launch_lane = new_frame ? 2'd0 : phase == 23 ? 2'd1 :
                             phase == 51 ? 2'd2 : 2'd3;
    wire [12:0] launch_frame = !running ? 13'd0 :
                               (wrap_frame ? frame + 1'b1 : frame);

    // A shifted token is independent of the frame phase. Capture requires
    // both witnesses; a missing capture invalidates this service.
    reg [19:0] visit_token;
    reg sampled, committed, damaged;
    // Two physical obligations sample the pad at the SAME edge. The
    // complement and sticky diagnostic also distinguish a lost primary hit.
    (* IOB="TRUE" *) reg sampled_err;
    (* DONT_TOUCH="TRUE" *) reg repair_a, repair_b;
    reg [15:0] seen;
    reg scan_bad, app_owner;
    wire sample_phase = phase == 5 || phase == 29 || phase == 57 || phase == 81;
    wire capture = protect_owner && visit_token[5] && sample_phase;
    wire missed_sample = protect_owner && visit_token[5] && !sample_phase;
    wire owes_write = repair_a || !repair_b;
    wire complete_read = protect_owner && visit_token[9] && !owes_write;
    wire complete_write = protect_owner && visit_token[19] && owes_write;
    reg [14:0] app_candidate;
    wire app_begin = phase==101 && app_request && !protect_owner;
    wire release_visit = complete_read || complete_write;
    wire addressed = seen == {1'b0,address};
    wire write_committed = committed && we_n && !drive;
    wire good_release = sampled && !damaged && addressed && !select_n &&
                        (!owes_write || write_committed) && !sealed;
    wire witness_disagrees = protect_owner && sampled && !visit_token[6] && (repair_a == repair_b);
    wire extra_write = !we_n && !owes_write;
    wire broken = phase_error || missed_sample || witness_disagrees || extra_write ||
                  (release_visit && !good_release);
    wire history_fault;
    native64_rule policy (
        .clk(clk), .cold(cold), .scan_start(scan_start), .common_end(common_end),
        .cut(cut), .install(install), .epoch(epoch),
        .packet(report_send), .packet_complete(sealed), .packet_epoch(epoch),
        .packet_count(count), .sealed(sealed),
        .scan_bad(scan_bad && !scan_start), .actual_count(count),
        .loss(loss || broken || (!active && !wait_ok) || (wrap_round && active && !installed) ||
              (protect_owner && visit_token[6] && sampled_err)),
        .issued(policy_level), .quiet(quiet), .accepted_zero(accepted_zero),
        .command_strobe(command_strobe), .history_fault(history_fault)
    );

    always @(posedge clk) begin
        if (cold) begin
            running<=0; active<=1; phase_a<=0; phase_inv<=8'hff; phase_parity<=0;
            frame<=0; epoch<=0;
            installed<=0;
            wait_rounds<=0; wait_parity<=0; visit_token<=0;
            address<=0; selected<=0; reading<=0; writing<=0; drive<=0;
            protect_owner<=0; app_owner<=0; app_grant<=0; app_valid<=0;
            sampled<=0;
            repair_a<=0;repair_b<=1;
            committed<=0; damaged<=0; seen<=0; count<=0; sealed<=0;
            scan_bad<=0; report_send<=0; execution_fault<=0;
        end else begin
            running<=1;
            report_send<=0; app_grant<=0; app_valid<=0;
            if(command_strobe) installed<=1;
            phase_a<=next_phase; phase_inv<=~next_phase; phase_parity<=^next_phase;
            if (running && wrap_frame) frame<=frame+1'b1;
            if (wrap_round && running) begin
                active<=next_active; epoch<=epoch+1'b1;
                wait_rounds<=next_wait; wait_parity<=^next_wait;
            end
            if (scan_start) begin
                installed<=0;
                seen<=0; count<=0; sealed<=0; scan_bad<=0;
            end
            visit_token<={visit_token[18:0],start_visit};
            if (start_visit) begin
                address<={launch_frame,launch_lane}; protect_owner<=1;
                selected<=1; reading<=1; writing<=0; drive<=0;
                sampled<=0;
                committed<=0; damaged<=0;
            end
            if (capture) begin
                sampled<=1;
            end
            if (protect_owner && visit_token[6]) begin
                reading<=0;repair_a<=sampled_err;repair_b<=!sampled_err;
            end
            if (broken || history_fault || (!active && !wait_ok)) execution_fault<=1;
            if (broken) begin scan_bad<=1; damaged<=1; end
            if (protect_owner && visit_token[9] && owes_write) drive<=1;
            if (protect_owner && visit_token[10] && owes_write) writing<=1;
            if (protect_owner && visit_token[15] && !we_n && drive && !select_n) begin
                writing<=0; committed<=1;
            end
            if (protect_owner && visit_token[17]) drive<=0;
            if (release_visit) begin
                protect_owner<=0; selected<=0; reading<=0; writing<=0; drive<=0;
                if (good_release) begin
                    seen<=seen+1'b1;
                    count<=count+{15'd0,owes_write};
                    if (&address) begin
                        sealed<=!scan_bad && !broken;
                        report_send<=!scan_bad && !broken;
                    end
                end
            end

            // Only reads are admitted for the long-lived payload. The
            // application never changes the protection report or the repair.
            if (phase==100) app_candidate<=app_address;
            if (app_begin) begin
                app_grant<=1; app_owner<=1; address<=app_candidate;
                selected<=1; reading<=1;
            end
            if (app_owner && phase==108) reading<=0;
            if (app_owner && phase==111) begin selected<=0; app_valid<=1; end
            if (phase==125) app_owner<=0;
        end
    end
    // Capture exactly once at +60 ns; hold this image through WE# rising.
    reg drive_next=0;
    // Independent idle values allow the address pad FF to reload each edge.
    // During every owned transaction its D equals the registered witness.
    always @(posedge clk) begin
        pad_address<=cold ? 15'd0 : start_visit ? {launch_frame,launch_lane} :
                     app_begin ? app_candidate : (protect_owner || app_owner) ? address : 15'd0;
    end
    // Opposite encoding to the fabric witnesses prevents feedback from a pad
    // Q into logic. At an idle pin the asynchronous SRAM is deselected.
    always @(posedge clk) begin
        if(cold) begin pad_select_n<=1; pad_oe_n<=1; pad_we_n<=1; end
        else begin
            pad_select_n<=!(start_visit || app_begin || (selected && !release_visit && !(app_owner && phase==111)));
            pad_oe_n<=!(start_visit || app_begin || (reading && !release_visit && !(protect_owner && visit_token[6]) && !(app_owner && phase==108)));
            pad_we_n<=!(!release_visit && !start_visit && ((protect_owner && visit_token[10] && owes_write) ||
                    (writing && !(protect_owner && visit_token[15] && drive && selected))));
        end
    end
    always @(posedge clk) begin
        if (capture) sampled_err<=err_in;
        if (capture || (app_owner && phase==107)) repair_image<=dq_in;
        if (app_owner && phase==108) app_data<=repair_image;
        dq_out<=repair_image;
        if(cold || visit_token[16]) drive_next<=0;
        else if(protect_owner && visit_token[8]) drive_next<=owes_write;
        pad_t_n<={16{!drive_next}};
    end
`ifdef FORMAL
    // Prove exact time position of every visit token and its reference phase.
    reg proof_past=0;
    genvar index;
    generate for(index=0;index<20;index=index+1) begin: token_position
        always @(posedge clk) if(proof_past && visit_token[index])
            assert(phase==index || phase==24+index || phase==52+index || phase==76+index);
    end endgenerate
    always @(posedge clk) begin
        proof_past<=1;
        if(proof_past) begin
            assert($onehot0(visit_token));
            assert(running || (phase==0 && visit_token==0));
            assert(phase<=139);
            assert(phase_a==~phase_inv && phase_parity==^phase_a);
        end
    end
`endif
endmodule

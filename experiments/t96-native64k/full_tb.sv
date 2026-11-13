// Independent pin scoreboard: integer absolute time, no DUT address,
// phase counter, release pulse or operation type drives the expected plan.
`timescale 1ns/1ns
module full_tb;
    reg clk=0, cold=1;
    always #5 clk=!clk;
    reg err=0;
    reg [15:0] dq=0;
    wire [14:0] addr;
    wire cs, oe, we, drive, owner, grant, app_valid, sealed, send, zero, install, fault;
    wire [15:0] out_data, app_data, count, repair_image, pad_t_n;
    wire [35:0] epoch;
    wire [3:0] issued;
    wire [9:0] quiet;
    reg app_req=0;
    localparam APP=15'h4567, WORDS=32768, LENGTH=1146880;
    native64_core dut(.clk(clk),.cold(cold),.loss(1'b0),.err_in(err),.dq_in(dq),
        .app_request(app_req),.app_address(APP),.app_grant(grant),.app_valid(app_valid),
        .app_data(app_data),.pad_address(addr),.pad_select_n(cs),.pad_oe_n(oe),.pad_we_n(we),.drive(drive),
        .dq_out(out_data),.protect_owner(owner),.issued(issued),.quiet(quiet),
        .pad_t_n(pad_t_n),.repair_image(repair_image),
        .sealed(sealed),.report_send(send),.count(count),.epoch(epoch),
        .accepted_zero(zero),.command_strobe(install),.execution_fault(fault));
    function automatic [15:0] image(input integer a);
        image=(a*173+16'ha5b7)&65535;
    endfunction
    integer scenario, pulse, tick, phase, lane, age, frame_no, address_plan;
    integer reads=0, writes=0, busy=0, app_ticks=0, sent=0, visible_count=0;
    integer seal_tick=-1, cut_tick=-1, command_tick=-1, next_tick=-1;
    integer last_sample=-1, last_commit=-1, last_release=-1;
    integer app_reads=0, actual_expected, base, stop, first_tick=-1;
    integer expected_app, expected_select, expected_oe, expected_we, expected_drive;
    integer max_busy=0, run_busy=0, partial_owner_ns=-1;
    reg [WORDS-1:0] visited=0;
    reg prior_we=1, prior_cs=1;
    reg hit, write_expected, prot, app_selected, app_oe;
    initial begin
        if (!$value$plusargs("case=%d",scenario)) scenario=0;
        if (!$value$plusargs("fault=%d",pulse)) pulse=0;
        stop=LENGTH; // includes first observed read of the next round
        repeat(3) @(posedge clk);
        for (tick=0;tick<=stop;tick=tick+1) begin
            @(negedge clk); cold=0;
            phase=tick%140;
            frame_no=(tick/LENGTH==0 ? tick/140 : 0);
            lane=phase<24 ? 0 : phase<52 ? 1 : phase<76 ? 2 : 3;
            case(lane) 0: base=0; 1: base=24; 2: base=52; default: base=76; endcase
            age=phase-base; address_plan=frame_no*4+lane;
            hit=scenario==2 || (scenario==1 && address_plan==WORDS-1) ||
                (pulse!=0 && address_plan==WORDS-1);
            // Faults 3 and 4 exercise two distinct, intentionally adverse
            // outcomes: a corrupted sampled value and a missing capture strobe.
            write_expected=hit && pulse!=3 && pulse!=4;
            // Only the +60 ns edge sees the correct data and ERR.
            err=(age==6) ? hit : !hit;
            dq=(age==6) ? image(address_plan) : ~image(address_plan);
            if (phase==108) dq=image(APP);
            expected_app=(frame_no%715==0);
            app_req=(phase==102 && expected_app);
            if (pulse==1 && address_plan==WORDS-1 && age==8) force dut.repair_a=0;
            if (pulse==2 && address_plan==WORDS-1 && age==6) dut.phase_a=dut.phase_a ^ 8'd2;
            if (pulse==3 && address_plan==WORDS-1 && age==7) force dut.sampled_err=0;
            if (pulse==4 && address_plan==WORDS-1 && age==6) force dut.capture=0;
            @(posedge clk); #1;
            if (pulse==1 && address_plan==WORDS-1 && age==20) release dut.repair_a;
            if (pulse==3 && address_plan==WORDS-1 && age==7) release dut.sampled_err;
            if (pulse==4 && address_plan==WORDS-1 && age==6) release dut.capture;
            begin
                prot=(age<(write_expected?20:10));
                app_selected=expected_app && phase>=102 && phase<112;
                app_oe=expected_app && phase>=102 && phase<109;
                expected_select=prot || app_selected;
                expected_oe=(prot && age<7) || app_oe;
                expected_we=prot && write_expected && age>=11 && age<16;
                expected_drive=prot && write_expected && age>=10 && age<18;
                if (owner!==prot || cs!==!expected_select || oe!==!expected_oe ||
                    we!==!expected_we || drive!==expected_drive || pad_t_n!=={16{!expected_drive}} ||
                    ((prot || app_selected) && addr!==(prot ? address_plan[14:0] : APP)))
                    $fatal(1,"pin plan mismatch tick=%0d addr=%0d expected=%0d",tick,addr,address_plan);
                if (prot && age==6) begin
                    if (pulse==4 && address_plan==WORDS-1) begin
                        if (dut.sampled || !err) $fatal(1,"missing capture sentinel did not fire");
                    end else if (repair_image!==image(address_plan) || dut.sampled_err!==hit)
                        $fatal(1,"aperture mismatch tick=%0d",tick);
                end
                if (drive && out_data!==image(address_plan)) $fatal(1,"write payload tick=%0d",tick);
                if (grant!==(expected_app && phase==102) || app_valid!==(expected_app && phase==112))
                    $fatal(1,"application handshake tick=%0d",tick);
                if (app_valid) begin
                    if(app_data!==image(APP)) $fatal(1,"application payload"); app_reads=app_reads+1;
                end
                if (tick<LENGTH) begin
                    // Observe [0,T) at +130 ns of the final dirty visit.
                    if (scenario==1 && pulse==0 && address_plan==WORDS-1 && age==13) begin
                        partial_owner_ns=busy*10;
                        if (sealed || send || !owner || we || writes!=0 || partial_owner_ns!=3276830)
                            $fatal(1,"truncated horizon rounded up or reported early");
                    end
                    if (owner) begin busy=busy+1; run_busy=run_busy+1;
                        if(run_busy>max_busy) max_busy=run_busy;
                    end else run_busy=0;
                    if(expected_app && phase>=102 && phase<126) app_ticks=app_ticks+1;
                    if(prior_cs && !cs && owner) begin
                        if(visited[addr] || addr!=reads) $fatal(1,"duplicate/order");
                        visited[addr]=1; reads=reads+1;
                    end
                    if (!prior_we && we) begin
                        writes=writes+1;
                        if(addr==WORDS-1) last_commit=tick;
                    end
                    if(address_plan==WORDS-1 && age==6) last_sample=tick;
                    if(address_plan==WORDS-1 && age==(write_expected?20:10)) last_release=tick;
                    if(age== (write_expected?20:10) && write_expected) visible_count=visible_count+1;
                    if(pulse==0 && count!==visible_count[15:0]) $fatal(1,"count before release tick=%0d",tick);
                    if(send) begin sent=sent+1; seal_tick=tick; end
                    actual_expected=(tick>=LENGTH-64+(scenario==0?10:20));
                    if(pulse==1 || pulse==2 || pulse==4) actual_expected=0;
                    if(sealed!==actual_expected[0]) $fatal(1,"premature/missing seal %0d",tick);
                    if(zero) cut_tick=tick;
                    if(install) command_tick=tick;
                    if(issued!=0 || quiet!=0 || stmt_fault()) $fatal(1,"unsafe first decision %0d",tick);
                end else begin
                    if(owner && !oe && we && !drive && addr==0) next_tick=tick;
                end
                prior_we=we; prior_cs=cs;
            end
        end
        if (reads!=WORDS || !(&visited) || writes!=
            ((scenario==2)?WORDS:(scenario==1 || pulse==1 || pulse==2)?1:0) ||
            busy!=10*(WORDS+writes) || sent!=((pulse==1 || pulse==2 || pulse==4)?0:1) || next_tick!=LENGTH ||
            command_tick!=LENGTH-10 || (scenario==0 && (pulse==0 || pulse==3) ? cut_tick!=LENGTH-30 : cut_tick!=-1))
            $fatal(1,"summary lacks required witness reads=%0d writes=%0d",reads,writes);
        $display("FULL case=%0d fault=%0d reads=%0d writes=%0d owner_ns=%0d longest_ns=%0d application_reads=%0d application_reserved_ns=%0d last_sample_ns=%0d last_WE_rise_ns=%0d last_release_ns=%0d seal_ns=%0d good_zero_ns=%0d command_ns=%0d next_ns=%0d partial_owner_ns=%0d",
            scenario,pulse,reads,writes,busy*10,max_busy*10,app_reads,app_ticks*10,
            pulse==4?-1:last_sample*10,last_commit<0?-1:last_commit*10,last_release*10,
            seal_tick<0?-1:seal_tick*10,cut_tick<0?-1:cut_tick*10,command_tick*10,next_tick*10,partial_owner_ns);
        $finish;
    end
    function automatic stmt_fault();
        stmt_fault=((pulse==0 || pulse==3) && fault) ||
                   ((pulse==1 || pulse==2) && tick>=LENGTH-64+9 && !fault) ||
                   (pulse==4 && tick>=LENGTH-64+10 && !fault);
    endfunction
endmodule

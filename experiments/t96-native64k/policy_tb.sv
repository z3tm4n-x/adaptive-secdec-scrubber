// Clock-level equivalence against an interval model. One iteration per L,
// one accepted packet per scheduled completed scan. Real scan spacing is
// checked in full_tb and join_tb using the SAME rule module.
`timescale 1ns/1ns
module policy_tb;
    reg clk=0,cold,start,common_end,cut,install,packet,complete,sealed,bad,loss;
    reg [35:0] epoch, tag;
    reg [15:0] cnt, actual;
    wire [3:0] issued;
    wire [9:0] quiet;
    wire zero,strobe,history_fault;
    native64_rule dut(.clk(clk),.cold(cold),.scan_start(start),.common_end(common_end),
        .cut(cut),.install(install),.epoch(epoch),.packet(packet),.packet_complete(complete),
        .packet_epoch(tag),.packet_count(cnt),.sealed(sealed),.scan_bad(bad),.loss(loss),
        .actual_count(actual),.issued(issued),.quiet(quiet),.accepted_zero(zero),
        .command_strobe(strobe),.history_fault(history_fault));
    task edge1; begin #3; clk=1; #1; clk=0; #1; end endtask
    integer thresholds[1:9];
    integer n, j, k, next_due, expected_z, expected_lev, samples, levels_seen, before_z;
    integer checked, cell_broken, valid_zero, scenario;
    function automatic integer desired(input integer z);
        integer i;
        begin desired=0; for(i=1;i<=9;i=i+1) if(z>=thresholds[i]) desired=i; end
    endfunction
    task clear_inputs;
        begin start=0;cut=0;install=0;packet=0;complete=0;sealed=0;bad=0;loss=0;cnt=0;actual=0;end
    endtask
    task restart;
        begin clear_inputs;epoch=0;tag=0;common_end=1;cold=1;edge1;cold=0;
            next_due=0; expected_z=0; expected_lev=0; cell_broken=0;end
    endtask
    task scan(input integer round_id,input integer defect);
        begin
            clear_inputs; epoch=round_id;tag=epoch;common_end=(round_id%512)==0;
            start=1;edge1;start=0;
            sealed=1;complete=1;actual=0;
            if(defect==1) begin actual=1;cnt=1;end // genuine ERR
            if(defect==2) complete=0;
            if(defect==3) tag=epoch-1;
            if(defect==4) sealed=0;
            if(defect==5) bad=1;
            // 6 missing, 7 first packet late, 8 exactly on cut, 9 duplicate.
            if(defect!=6 && defect!=7 && defect!=8) begin packet=1;edge1;packet=0;end
            if(defect==9 || defect==10) begin
                if(defect==10) cnt=1;packet=1;edge1;packet=0;
            end
            if(defect==11) begin loss=1;edge1;loss=0;end
            if(defect==12) begin // Reached good history. Flip one physical history bit.
                before_z=quiet; dut.quiet=quiet ^ 10'd8;
                #1;if(!history_fault) $fatal(1,"history upset undetected");
                edge1;
            end
            if(defect==13) begin // an intact share of zero is not evidence for a bad count
                actual=1;
            end
            if(defect==8) packet=1;
            cut=1;edge1;cut=0;packet=0;
            valid_zero=(defect==0 || defect==8 || defect==9);
            if(zero!==valid_zero[0]) $fatal(1,"cut round=%0d defect=%0d",round_id,defect);
            if(!valid_zero) begin expected_z=0;expected_lev=0;cell_broken=1;end
            if(cell_broken && !common_end) expected_lev=0;
            if(common_end) begin
                if(round_id!=0 && valid_zero && !cell_broken && expected_z<596)
                    expected_z=expected_z+1;
                else if(!valid_zero || cell_broken || round_id==0) expected_z=0;
                expected_lev=desired(expected_z);cell_broken=0;
            end
            if(defect==7) begin packet=1;edge1;packet=0;end
            install=1;edge1;install=0;
            if(!strobe || quiet!=expected_z || issued!=expected_lev)
                $fatal(1,"rule round=%0d case=%0d z=%0d/%0d level=%0d/%0d",
                       round_id,defect,quiet,expected_z,issued,expected_lev);
            if(common_end && scenario==0)
                levels_seen=levels_seen | (1<<issued);
            next_due=round_id+(1<<expected_lev);samples=samples+1;
        end
    endtask
    initial begin
        thresholds[1]=3;thresholds[2]=5;thresholds[3]=10;thresholds[4]=19;
        thresholds[5]=38;thresholds[6]=75;thresholds[7]=149;
        thresholds[8]=298;thresholds[9]=596;
        samples=0;levels_seen=0;checked=0;
        for(scenario=0;scenario<=15;scenario=scenario+1) begin
            restart;
            if(scenario==0) begin
                for(n=0;n<=599*512;n=n+1) if(n==next_due) scan(n,0);
                if(quiet!=596 || issued!=9 || levels_seen!=1023) $fatal(1,"threshold coverage");
            end else begin
                // Reach nontrivial state legitimately; spoil on a non-common
                // scan, then verify the entire recovery and first new promotion.
                for(n=0;n<=9*512;n=n+1) if(n==next_due)
                    scan(n,(scenario==14 && n==4*512) ? 6 :
                           (scenario==15 && n==4*512) ? 1 :
                           (scenario<=13 && n==4*512+2) ? scenario : 0);
                checked=checked+1;
            end
        end
        // Loss at a common cut, then 3 complete new cells; late after install
        // must never cancel a committed gap. A faulty proposal before install
        // must fall back without creating a usable historical cell.
        restart;
        for(n=0;n<=3*512;n=n+1) if(n==next_due) scan(n,0);
        if(issued!=1) $fatal(1,"unreachable seeded history");
        loss=1;edge1;loss=0;
        if(issued!=1 || quiet!=0) $fatal(1,"retroactive cancellation");
        expected_z=0;cell_broken=1;
        scan(next_due,0);
        if(issued!=0) $fatal(1,"first open decision");
        $display("POLICY levels_mask=%0d saturation=596 samples=%0d report_cases=%0d post_install_loss=1",levels_seen,samples,checked);
        $finish;
    end
endmodule

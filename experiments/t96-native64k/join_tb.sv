// Interface composition. A reachable policy prefix from policy_tb is loaded
// at the start of a boundary scan. No scan completion or zero is injected.
// Elide only frames explicitly identified below; count real last-address pins.
`timescale 1ns/1ns
module join_tb;
    reg clk=0,cold=1,loss=0;
    wire cs,oe,we,drive,owner,sealed,packet,zero,install;
    wire [14:0] addr; wire [3:0] issued; wire [9:0] z;
    wire [35:0] epoch; wire [15:0] count;
    native64_core dut(.clk(clk),.cold(cold),.loss(loss),.dq_in(16'ha5bf),.err_in(1'b0),
        .app_request(1'b0),.app_address(15'd0),.pad_select_n(cs),.pad_oe_n(oe),.pad_we_n(we),
        .drive(drive),.pad_address(addr),.protect_owner(owner),.sealed(sealed),
        .report_send(packet),.accepted_zero(zero),.command_strobe(install),
        .issued(issued),.quiet(z),.epoch(epoch),.count(count));
    task edge1; begin #5;clk=1;#1;clk=0;#4;end endtask
    integer thresholds[1:9], level_no, defect, i, n, now_tick, reads, next_base,
            last_tick, expected_level, delivered, mode;
    reg previous;
    localparam LENGTH=1146880;
    initial begin
        thresholds[1]=3;thresholds[2]=5;thresholds[3]=10;thresholds[4]=19;
        thresholds[5]=38;thresholds[6]=75;thresholds[7]=149;
        thresholds[8]=298;thresholds[9]=596;
        if(!$value$plusargs("level=%d",level_no)) level_no=1;
        if(!$value$plusargs("defect=%d",defect)) defect=0;
        edge1;cold=0;edge1;
        // Just-launched visit zero. A bounded reachable prefix on a common
        // boundary; the unaccelerated policy enumerator established the state.
        dut.epoch=36'd512*thresholds[level_no]; dut.policy.initialized=1;
        dut.policy.quiet=thresholds[level_no]-1;
        dut.policy.quiet_inv=~dut.policy.quiet; dut.policy.issued=level_no-1;
        reads=0;previous=1;last_tick=-1;delivered=0;
        for(now_tick=0;now_tick<LENGTH;now_tick=now_tick+1) begin
            if(now_tick>0) edge1;
            if(!cs && !oe && we && !drive && previous) begin
                if(addr!=reads[14:0]) $fatal(1,"out of order epoch boundary");
                reads=reads+1;
            end
            previous=cs;
            if(packet && last_tick<0) begin
                if(addr!=32767 || !sealed || owner || !cs || count!=0)
                    $fatal(1,"packet without completed clean visit");
                last_tick=now_tick;
                if(defect==1 || defect==2 || defect==3) force dut.report_send=0;
            end
            // Set up the existing complete local packet just before the cut,
            // or just AFTER it (five ns later in physical first-arrival test).
            if(now_tick==LENGTH-31 && defect==1) force dut.report_send=1;
            if(now_tick==LENGTH-30) begin
                delivered=zero;
                if(defect==1) begin release dut.report_send;dut.report_send=0;end
                if(defect==2) force dut.report_send=1;
                if(defect==4) begin // legal code not authorized after quiet upset
                    dut.policy.quiet=dut.policy.quiet^10'd8;
                end
                if(defect==5) begin // corrupted command or lost installation
                    dut.policy.proposed=dut.policy.proposed^4'd1;
                end
            end
            if(now_tick==LENGTH-29 && defect==2) begin release dut.report_send;dut.report_send=0;end
            if(now_tick==LENGTH-10) begin
                expected_level=(defect==0 || defect==1) ? level_no : 0;
                if(!install || issued!=expected_level) $fatal(1,"install %0d %0d",issued,expected_level);
            end
        end
        if(defect==3) begin release dut.report_send;dut.report_send=0;end
        if(reads!=32768 || last_tick!=LENGTH-54 || delivered!=(defect==0 || defect==1 || defect>=4))
            $fatal(1,"join full scan or inclusive cut");
        // Check EVERY inactive round boundary. For level 1 also clock all
        // 1,146,880 idle ticks. For the other levels skip only interiors of
        // inactive base rounds; preserve the real wait, epoch and command.
        next_base=1<<expected_level;
        for(n=1;n<=next_base;n=n+1) begin
            edge1;
            if(n==next_base) begin
                if(cs || oe || !we || drive || !owner || addr!=0)
                    $fatal(1,"missing real next transaction");
            end else begin
                if(!cs || owner || !we || drive) $fatal(1,"early start");
                if(level_no==1) begin
                    for(i=1;i<LENGTH;i=i+1) begin edge1;
                        if(owner || !cs || !we || drive) $fatal(1,"pin in literal quiet gap");
                    end
                end else begin
                    dut.frame=8191;dut.phase_a=139;dut.phase_inv=~8'd139;dut.phase_parity=^8'd139;
                end
            end
        end
        $display("JOIN level=%0d defect=%0d physical_reads=%0d zero_at_cut=%0d next_rounds=%0d literal_idle=%0d",level_no,defect,reads,delivered,next_base,level_no==1 && next_base>1);
        $finish;
    end
endmodule

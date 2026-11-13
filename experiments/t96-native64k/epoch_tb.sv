// Joined epoch recovery test. Observe physical pins and compare with the
// common-cell rule. Subsequent clean scans skip only an idle frame boundary
// and its preceding clean address prefix. Every basal boundary is executed.
`timescale 1ns/1ns
module epoch_tb;
    localparam integer L=1146880, LAST=L-64, FIRST=1536;
    localparam [15:0] DATA=16'ha5bf;
    reg clk=0,cold=1,loss=0,err=0;
    wire cs,oe,we,owner,drive,sent,zero,strobe;
    wire [14:0] addr; wire [15:0] dq;
    wire [9:0] z; wire [3:0] issued; wire [35:0] epoch;
    native64_core dut(.clk(clk),.cold(cold),.loss(loss),.err_in(err),.dq_in(DATA),
        .app_request(1'b0),.app_address(15'b0),
        .pad_select_n(cs),.pad_oe_n(oe),.pad_we_n(we),.pad_address(addr),.dq_out(dq),
        .protect_owner(owner),.drive(drive),.report_send(sent),.accepted_zero(zero),
        .command_strobe(strobe),.quiet(z),.issued(issued),.epoch(epoch));
    task tick; begin #5;clk=1;#1;clk=0;#4;end endtask
    integer mode,old,ep,t,reads=0,published=0,writes=0,common_no,goal,cut_z;
    integer next_due=FIRST,first_promote=-1,commands=0,code=-1,broken_cell;
    reg prior_cs,prior_we,started,expect_active;
    initial begin
        if(!$value$plusargs("mode=%d",mode) || mode<0 || mode>3) $fatal;
        if(!$value$plusargs("old=%d",old)) old=0;
        tick;cold=0;tick;
        dut.epoch=FIRST;dut.policy.initialized=1;dut.policy.quiet=2;
        dut.policy.quiet_inv=~10'd2;
        for(ep=FIRST;ep<=FIRST+4*512+2;ep=ep+1) begin
            expect_active=(ep==next_due);
            started=(!cs && !oe && we && owner && addr==0);
            if(epoch!=ep || started!==expect_active) $fatal(1,"start ep=%d due=%d",ep,next_due);
            if(ep==FIRST || ep%512<=2 && ep>=FIRST+512 && (ep%512==0 || ep>=FIRST+3*512))
                $display("START epoch=%0d address0=%0d",ep,started);
            prior_cs=1;prior_we=1;code=-1;cut_z=-1;
            for(t=0;t<L;t=t+1) begin
                if(t>0) begin
                    err=(ep==FIRST && t==LAST+6);
                    tick;
                end
                if(ep==FIRST) begin
                    if(!cs && !oe && owner && prior_cs) begin
                        if(addr!=reads) $fatal(1,"address %d",addr);
                        reads=reads+1;
                    end
                    if(t==LAST+6 && !(dut.sampled && dut.sampled_err && dut.repair_image==DATA)) $fatal;
                    if(t==LAST+19 && (!owner || cs)) $fatal(1,"early release");
                    if(t==LAST+20 && (owner || !cs || dut.sealed)) $fatal(1,"bad final release");
                    if(t==LAST+8) begin
                        if(!dut.repair_a || dut.repair_b) $fatal;
                        dut.repair_a=0;
                    end
                    if(!we && (addr!=32767 || !drive || dq!==DATA)) $fatal(1,"bad write data");
                    if(!prior_we && we) begin
                        if(t!=LAST+16 || cs || !drive || dq!==DATA) $fatal(1,"WE timing");
                        writes=writes+1;
                    end
                    if(sent) published=published+1;
                end
                if(ep!=FIRST && t==136) begin
                    // All four visits of this frame have released. Advance to
                    // the same idle point before the final frame. The checker
                    // never seeds the rule, report, cut or next actual start.
                    if(!cs || owner || dut.visit_token!=0 || dut.phase!=136 || dut.frame!=0) $fatal;
                    dut.frame=8190;
                    if(started) begin
                        if(dut.seen!=4 || dut.count!=0 || !we) $fatal;
                        dut.seen=32764;
                    end
                    t=8190*140+136;
                end
                if(started && t==L-30) begin
                    common_no=(ep-FIRST)/512;
                    if(ep==FIRST && (zero || published!=0 || reads!=32768 || writes!=1 ||
                                      !dut.policy.invalid || dut.policy.spoiled)) $fatal(1,"first cut");
                    if(ep==FIRST) begin
                        if(mode==1 || mode==2) loss=1;       // continuous or one edge
                        if(mode==3) dut.phase_a=dut.phase_a ^ 1; // new local broken edge
                    end
                    if(ep%512==0) begin
                        broken_cell=(old!=0 || mode==2 || mode==3);
                        goal=common_no-broken_cell;
                        if(goal<0 || mode==1) goal=0;
                        if(z!=goal || (common_no>0 && zero!==(mode!=1))) $fatal(1,"cut ep=%d z=%d expected=%d",ep,z,goal);
                        cut_z=z;
                    end
                end
                if(ep==FIRST && t==L-29) begin
                    if(dut.policy.spoiled !== (old!=0 || mode!=0)) $fatal(1,"old epoch replay or missed new loss");
                    if(mode==2) loss=0;
                end
                if(strobe) begin
                    if(!started || t!=L-10 || code!=-1) $fatal(1,"install phase");
                    code=issued;commands=commands+1;
                    if(ep%512==0) begin
                        if(code!=(cut_z>=3)) $fatal(1,"install ep=%d",ep);
                        $display("CELL mode=%0d old=%0d epoch=%0d quiet=%0d period_L=%0d",mode,old,ep,cut_z,1<<code);
                    end
                    if(code==1 && first_promote<0) first_promote=ep;
                end
                prior_cs=cs;prior_we=we;
            end
            if(started) begin
                if(code<0) $fatal(1,"missing installation");
                next_due=ep+(1<<code);
            end
            tick; // apply the genuine wrap and observe address zero next iteration
        end
        if(first_promote!=(mode==1 ? -1 : FIRST+(old!=0 || mode>=2 ? 4 : 3)*512)) $fatal;
        $display("EPOCH mode=%0d old=%0d reads=%0d writes=%0d sample_ns=%0d WE_rise_ns=%0d release_ns=%0d report=%0d cut_ns=%0d install_ns=%0d first_2L_epoch=%0d commands=%0d",
             mode,old,reads,writes,(LAST+6)*10,(LAST+16)*10,(LAST+20)*10,published,(L-30)*10,(L-10)*10,first_promote,commands);
        $finish;
    end
endmodule

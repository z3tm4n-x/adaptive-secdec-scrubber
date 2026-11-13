// Exhaustive induction on the small obligations used by the composed checks.
// Unconstrained data, round indices/markers and qualification inputs. Cold
// initialization precedes the first operation. No hidden memory state.
module policy_safety;
    wire clk;
    (* anyseq *) reg cold, start, boundary, cut, install, packet, complete, sealed, bad, loss;
    (* anyseq *) reg [35:0] epoch, tag;
    (* anyseq *) reg [15:0] count, actual;
    wire [3:0] issued; wire [9:0] quiet; wire zero, command, fault;
    native64_rule dut(clk,cold,start,boundary,cut,install,epoch,packet,complete,tag,
                      count,sealed,bad,loss,actual,issued,quiet,zero,command,fault);
    reg past=0;
    always @(posedge clk) begin
        past<=1;
        if(!past) assume(cold);
        if(past) begin
            assert(issued<=9 && quiet<=596);
            if(zero) assert($past(cut && !cold && sealed && !bad && !loss && actual==0));
            if(!$past(cold || install)) assert(issued==$past(issued));
            if(quiet>$past(quiet)) begin
                assert($past(cut && boundary && !cold)); assert(quiet==$past(quiet)+1);
            end
            if($past(!cold && install && loss)) assert(issued==0);
        end
    end
endmodule

module pins_agree;
    wire clk;
    (* anyseq *) reg cold, loss, err, req;
    (* anyseq *) reg [15:0] dq;
    (* anyseq *) reg [14:0] app;
    wire [14:0] address,pad_address;
    wire cs,oe,we,pcs,poe,pwe;
    native64_core dut(.clk(clk),.cold(cold),.loss(loss),.err_in(err),.dq_in(dq),
        .app_request(req),.app_address(app),.address(address),.select_n(cs),.oe_n(oe),.we_n(we),
        .pad_address(pad_address),.pad_select_n(pcs),.pad_oe_n(poe),.pad_we_n(pwe));
    reg past=0;
    always @(posedge clk) begin
        past<=1; if(!past) assume(cold);
        if(past) assert({address,cs,oe,we}=={pad_address,pcs,poe,pwe});
    end
endmodule

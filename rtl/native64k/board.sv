// Selected ZedBoard/FMC demonstration. CY62167GE30's CE2 and BYTE are high.
module native64_board (
    input wire ref100, sram_err,
    inout wire [15:0] sram_dq,
    output wire [19:0] sram_a,
    output wire sram_ce_n, sram_oe_n, sram_we_n, sram_ub_n, sram_lb_n,
    output wire locked_led, fault_led
);
    wire clk, ref_i, fb_i, fb, clk_i, locked;
    IBUF input_buffer(.I(ref100),.O(ref_i));
    MMCME2_BASE #(.CLKIN1_PERIOD(10.0),.CLKFBOUT_MULT_F(10.0),
        .CLKOUT0_DIVIDE_F(10.0),.DIVCLK_DIVIDE(1),.REF_JITTER1(0.005)) mmcm(
        .CLKIN1(ref_i),.CLKFBIN(fb),.CLKFBOUT(fb_i),.CLKOUT0(clk_i),
        .PWRDWN(1'b0),.RST(1'b0),.LOCKED(locked));
    BUFG feedback(.I(fb_i),.O(fb));
    BUFG clock_buffer(.I(clk_i),.O(clk));
    // Qualified clean memory and valid reference clock before configuration.
    // Only configuration starts a new mission; no run-time reset pin.
    (* SHREG_EXTRACT="NO" *) reg [3:0] startup=0;
    (* ASYNC_REG="TRUE" *) reg [1:0] lock_sync=0;
    always @(posedge clk) begin
        lock_sync<={lock_sync[0],locked};
        if(lock_sync[1]) startup<={startup[2:0],1'b1};
    end
    wire cold=!startup[3];
    wire [15:0] dq_in,dq_out,app_data;
    wire [14:0] address;
    wire drive, app_grant, app_valid;
    wire [15:0] pad_t_n;
    wire [3:0] issued;
    wire active_owner;
    assign sram_a={5'b0,address};
    assign sram_lb_n=0;
    assign sram_ub_n=0;
    genvar b;
    generate for(b=0;b<16;b=b+1) begin: io
        IOBUF dq(.IO(sram_dq[b]),.I(dq_out[b]),.O(dq_in[b]),.T(pad_t_n[b]));
    end endgenerate

    // Read-only fabric client. Hold request until a reserved slot accepts it.
    // Minimum inter-grant time exceeds the 1,000,020 ns application envelope.
    reg [16:0] app_rest=0;
    reg [14:0] app_addr=0;
    reg observed=0;
    always @(posedge clk) begin
        if(app_grant) begin app_rest<=17'd100003; app_addr<=app_addr+1'b1; end
        else if(app_rest!=0) app_rest<=app_rest-1'b1;
        if(app_valid) observed<=^app_data;
    end
    native64_core core(.clk(clk),.cold(cold),.loss(1'b0),.dq_in(dq_in),.err_in(sram_err),
         .app_request(app_rest==0),.app_address(app_addr),.app_grant(app_grant),
         .app_valid(app_valid),.app_data(app_data),.pad_address(address),
         .pad_select_n(sram_ce_n),.pad_oe_n(sram_oe_n),.pad_we_n(sram_we_n),.drive(drive),
         .dq_out(dq_out),.pad_t_n(pad_t_n),.issued(issued),.protect_owner(active_owner),
         .execution_fault(fault_led));
    reg monitor=0;
    always @(posedge clk) monitor<=observed ^ (^issued) ^ active_owner;
    assign locked_led=monitor;
endmodule

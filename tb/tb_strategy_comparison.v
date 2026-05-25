`timescale 1ns/1ps

module tb_strategy_comparison;

parameter ADDR_WIDTH = 4;
localparam CODEWORD_WIDTH = 39;
localparam LEVEL_WIDTH = 3;
localparam INTERVAL_WIDTH = 32;
localparam DEPTH = (1 << ADDR_WIDTH);

localparam DEFAULT_TOTAL_RUN_CYCLES = 1300;
localparam MAX_FAULT_EVENTS = 100000;
localparam MAX_CONTROL_EVENTS = 100000;

localparam MODE_FIXED     = 2'd0;
localparam MODE_TABLE     = 2'd1;
localparam MODE_THRESHOLD = 2'd2;

reg clk;
reg rst;
reg enable;

reg [1:0] mode;

reg [LEVEL_WIDTH-1:0] ctrl_level;
reg ctrl_valid;
reg ctrl_update;

reg [INTERVAL_WIDTH-1:0] fixed_interval;
reg [INTERVAL_WIDTH-1:0] safe_interval;
reg [31:0] max_control_age;

reg [INTERVAL_WIDTH-1:0] level0_interval;
reg [INTERVAL_WIDTH-1:0] level1_interval;
reg [INTERVAL_WIDTH-1:0] level2_interval;
reg [INTERVAL_WIDTH-1:0] level3_interval;
reg [INTERVAL_WIDTH-1:0] level4_interval;
reg [INTERVAL_WIDTH-1:0] level5_interval;
reg [INTERVAL_WIDTH-1:0] level6_interval;
reg [INTERVAL_WIDTH-1:0] level7_interval;

reg [LEVEL_WIDTH-1:0] threshold_low_to_medium;
reg [LEVEL_WIDTH-1:0] threshold_medium_to_low;
reg [LEVEL_WIDTH-1:0] threshold_medium_to_high;
reg [LEVEL_WIDTH-1:0] threshold_high_to_medium;

reg [INTERVAL_WIDTH-1:0] threshold_low_interval;
reg [INTERVAL_WIDTH-1:0] threshold_medium_interval;
reg [INTERVAL_WIDTH-1:0] threshold_high_interval;

wire ctrl_read_en;
wire [ADDR_WIDTH-1:0] ctrl_read_addr;
wire [CODEWORD_WIDTH-1:0] mem_read_data;

wire ctrl_write_en;
wire [ADDR_WIDTH-1:0] ctrl_write_addr;
wire [CODEWORD_WIDTH-1:0] ctrl_write_data;

/*
 * В режиме начальной записи памятью управляет проверочная среда.
 * После инициализации памятью управляет контроллер.
 */
reg tb_mode;

reg tb_read_en;
reg [ADDR_WIDTH-1:0] tb_read_addr;

reg tb_write_en;
reg [ADDR_WIDTH-1:0] tb_write_addr;
reg [CODEWORD_WIDTH-1:0] tb_write_data;

reg tb_inject_en;
reg [ADDR_WIDTH-1:0] tb_inject_addr;
reg [CODEWORD_WIDTH-1:0] tb_inject_mask;

wire mem_read_en;
wire [ADDR_WIDTH-1:0] mem_read_addr;

wire mem_write_en;
wire [ADDR_WIDTH-1:0] mem_write_addr;
wire [CODEWORD_WIDTH-1:0] mem_write_data;

assign mem_read_en   = tb_mode ? tb_read_en   : ctrl_read_en;
assign mem_read_addr = tb_mode ? tb_read_addr : ctrl_read_addr;

assign mem_write_en   = tb_mode ? tb_write_en   : ctrl_write_en;
assign mem_write_addr = tb_mode ? tb_write_addr : ctrl_write_addr;
assign mem_write_data = tb_mode ? tb_write_data : ctrl_write_data;

reg [31:0] encoder_data_in;
wire [38:0] encoded_codeword;

wire scrub_active;
wire [31:0] scrub_cycle_count;
wire [31:0] memory_read_count;
wire [31:0] memory_write_count;
wire [31:0] corrected_error_count;
wire [31:0] uncorrectable_error_count;
wire [31:0] interval_switch_count;

wire [31:0] total_cycle_count;
wire [31:0] scrub_active_cycle_count;
wire [31:0] memory_busy_cycle_count;
wire [31:0] safe_mode_cycle_count;
wire [31:0] safe_mode_entry_count;

wire [INTERVAL_WIDTH-1:0] selected_interval;
wire safe_mode_active;
wire [LEVEL_WIDTH-1:0] current_level;
wire [1:0] threshold_state;
wire [31:0] control_age;
wire [INTERVAL_WIDTH-1:0] effective_wait_interval;
wire [31:0] last_pass_duration;

wire [38:0] checked_corrected_codeword;
wire [31:0] checked_data_out;
wire checked_single_error;
wire checked_double_error;
wire checked_uncorrectable;
wire [5:0] checked_error_position;

integer strategy_id;
reg [127:0] strategy_name;

integer sim_cycle;
integer total_run_cycles;
integer configured_fixed_interval;
integer configured_safe_interval;

integer configured_level0_interval;
integer configured_level1_interval;
integer configured_level2_interval;
integer configured_level3_interval;
integer configured_level4_interval;
integer configured_level5_interval;
integer configured_level6_interval;
integer configured_level7_interval;

integer configured_threshold_low_to_medium;
integer configured_threshold_medium_to_low;
integer configured_threshold_medium_to_high;
integer configured_threshold_high_to_medium;

integer configured_threshold_low_interval;
integer configured_threshold_medium_interval;
integer configured_threshold_high_interval;

integer trace_execution;
integer trace_file;
integer previous_trace_scrub_cycle_count;
integer dump_vcd;
reg [1023:0] trace_output_path;

integer i;
integer error_count;
integer injected_event_count;
integer csv_file;
integer busy_per_mille;
integer scrub_per_mille;
integer safe_per_mille;
integer unique_uncorrectable_word_count;

integer fault_event_time [0:MAX_FAULT_EVENTS-1];
integer fault_event_addr [0:MAX_FAULT_EVENTS-1];
reg [CODEWORD_WIDTH-1:0] fault_event_mask [0:MAX_FAULT_EVENTS-1];

integer fault_event_count;
integer fault_event_index;
integer fault_file;
integer fault_read_count;
integer fault_time_value;
integer fault_addr_value;
reg [CODEWORD_WIDTH-1:0] fault_mask_value;

integer control_event_time [0:MAX_CONTROL_EVENTS-1];
integer control_event_level [0:MAX_CONTROL_EVENTS-1];

integer control_event_count;
integer control_event_index;
integer control_file;
integer control_read_count;
integer control_time_value;
integer control_level_value;

integer snap_total_cycle_count;
integer snap_scrub_cycle_count;
integer snap_memory_read_count;
integer snap_memory_write_count;
integer snap_corrected_error_count;
integer snap_uncorrectable_error_count;
integer snap_interval_switch_count;
integer snap_safe_mode_entry_count;
integer snap_safe_mode_cycle_count;
integer snap_scrub_active_cycle_count;
integer snap_memory_busy_cycle_count;

secded_32_39_encoder encoder_inst (
    .data_in(encoder_data_in),
    .codeword_out(encoded_codeword)
);

secded_32_39_decoder checker_decoder_inst (
    .codeword_in(mem_read_data),
    .codeword_corrected(checked_corrected_codeword),
    .data_out(checked_data_out),
    .single_error(checked_single_error),
    .double_error(checked_double_error),
    .uncorrectable(checked_uncorrectable),
    .error_position(checked_error_position)
);

protected_memory_model #(
    .ADDR_WIDTH(ADDR_WIDTH),
    .CODEWORD_WIDTH(CODEWORD_WIDTH)
) memory_inst (
    .clk(clk),

    .read_en(mem_read_en),
    .read_addr(mem_read_addr),
    .read_data(mem_read_data),

    .write_en(mem_write_en),
    .write_addr(mem_write_addr),
    .write_data(mem_write_data),

    .inject_en(1'b0),
    .inject_addr({ADDR_WIDTH{1'b0}}),
    .inject_bit(6'd0),

    .inject_mask_en(tb_inject_en),
    .inject_mask_addr(tb_inject_addr),
    .inject_mask(tb_inject_mask)
);

adaptive_scrub_controller #(
    .ADDR_WIDTH(ADDR_WIDTH),
    .CODEWORD_WIDTH(CODEWORD_WIDTH),
    .LEVEL_WIDTH(LEVEL_WIDTH),
    .INTERVAL_WIDTH(INTERVAL_WIDTH)
) controller_inst (
    .clk(clk),
    .rst(rst),
    .enable(enable),

    .mode(mode),

    .ctrl_level(ctrl_level),
    .ctrl_valid(ctrl_valid),
    .ctrl_update(ctrl_update),

    .fixed_interval(fixed_interval),
    .safe_interval(safe_interval),
    .max_control_age(max_control_age),

    .level0_interval(level0_interval),
    .level1_interval(level1_interval),
    .level2_interval(level2_interval),
    .level3_interval(level3_interval),
    .level4_interval(level4_interval),
    .level5_interval(level5_interval),
    .level6_interval(level6_interval),
    .level7_interval(level7_interval),

    .threshold_low_to_medium(threshold_low_to_medium),
    .threshold_medium_to_low(threshold_medium_to_low),
    .threshold_medium_to_high(threshold_medium_to_high),
    .threshold_high_to_medium(threshold_high_to_medium),

    .threshold_low_interval(threshold_low_interval),
    .threshold_medium_interval(threshold_medium_interval),
    .threshold_high_interval(threshold_high_interval),

    .mem_read_en(ctrl_read_en),
    .mem_read_addr(ctrl_read_addr),
    .mem_read_data(mem_read_data),

    .mem_write_en(ctrl_write_en),
    .mem_write_addr(ctrl_write_addr),
    .mem_write_data(ctrl_write_data),

    .scrub_active(scrub_active),
    .scrub_cycle_count(scrub_cycle_count),
    .memory_read_count(memory_read_count),
    .memory_write_count(memory_write_count),
    .corrected_error_count(corrected_error_count),
    .uncorrectable_error_count(uncorrectable_error_count),
    .interval_switch_count(interval_switch_count),

    .total_cycle_count(total_cycle_count),
    .scrub_active_cycle_count(scrub_active_cycle_count),
    .memory_busy_cycle_count(memory_busy_cycle_count),
    .safe_mode_cycle_count(safe_mode_cycle_count),
    .safe_mode_entry_count(safe_mode_entry_count),

    .selected_interval(selected_interval),
    .safe_mode_active(safe_mode_active),
    .current_level(current_level),
    .threshold_state(threshold_state),
    .control_age(control_age),
    .effective_wait_interval(effective_wait_interval),
    .last_pass_duration(last_pass_duration)
);

initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
end

task write_memory_word;
    input [ADDR_WIDTH-1:0] addr;
    input [31:0] data;
    begin
        encoder_data_in = data;
        #1;

        tb_write_addr = addr;
        tb_write_data = encoded_codeword;
        tb_write_en = 1'b1;

        @(posedge clk);
        #1;

        tb_write_en = 1'b0;
    end
endtask

task read_memory_word;
    input [ADDR_WIDTH-1:0] addr;
    begin
        tb_read_addr = addr;
        tb_read_en = 1'b1;

        @(posedge clk);
        #1;

        tb_read_en = 1'b0;
    end
endtask

task configure_run_length;
    begin
        if (!$value$plusargs("TOTAL_RUN_CYCLES=%d", total_run_cycles)) begin
            total_run_cycles = DEFAULT_TOTAL_RUN_CYCLES;
        end

        if (total_run_cycles <= 0) begin
            $display("ERROR: TOTAL_RUN_CYCLES must be positive");
            $display("  actual = %0d", total_run_cycles);
            $fatal(1);
        end

        $display("Total run cycles: %0d", total_run_cycles);
    end
endtask

task configure_strategy;
    begin
        if (!$value$plusargs("STRATEGY=%d", strategy_id)) begin
            strategy_id = 0;
        end

        /*
         * Общие параметры.
         * По умолчанию сохраняются прежние демонстрационные значения.
         * Paper/risk-policy конфигурация передаётся через plusargs.
         */
        configured_safe_interval = 5;

        if (!$value$plusargs("SAFE_INTERVAL=%d", configured_safe_interval)) begin
            configured_safe_interval = 5;
        end

        if (configured_safe_interval <= 0) begin
            $display("ERROR: SAFE_INTERVAL must be positive");
            $display("  actual = %0d", configured_safe_interval);
            $fatal(1);
        end

        safe_interval = configured_safe_interval[INTERVAL_WIDTH-1:0];

        /*
         * В сравнительном эксперименте безопасный режим не должен включаться
         * только из-за окончания расписания управляющих уровней.
         */
        max_control_age = total_run_cycles + 100;

        /*
         * Таблица уровень -> model-cycle interval.
         *
         * Для paper/risk-policy режима эта таблица задаёт нормированное
         * отображение расчётных физических интервалов статьи 3 в интервалы
         * ускоренного RTL-стенда. Это не физические секунды RTL-модели.
         */
        configured_level0_interval = 100;
        configured_level1_interval = 80;
        configured_level2_interval = 60;
        configured_level3_interval = 40;
        configured_level4_interval = 25;
        configured_level5_interval = 15;
        configured_level6_interval = 10;
        configured_level7_interval = 5;

        if (!$value$plusargs("LEVEL0_INTERVAL=%d", configured_level0_interval)) begin
            configured_level0_interval = 100;
        end
        if (!$value$plusargs("LEVEL1_INTERVAL=%d", configured_level1_interval)) begin
            configured_level1_interval = 80;
        end
        if (!$value$plusargs("LEVEL2_INTERVAL=%d", configured_level2_interval)) begin
            configured_level2_interval = 60;
        end
        if (!$value$plusargs("LEVEL3_INTERVAL=%d", configured_level3_interval)) begin
            configured_level3_interval = 40;
        end
        if (!$value$plusargs("LEVEL4_INTERVAL=%d", configured_level4_interval)) begin
            configured_level4_interval = 25;
        end
        if (!$value$plusargs("LEVEL5_INTERVAL=%d", configured_level5_interval)) begin
            configured_level5_interval = 15;
        end
        if (!$value$plusargs("LEVEL6_INTERVAL=%d", configured_level6_interval)) begin
            configured_level6_interval = 10;
        end
        if (!$value$plusargs("LEVEL7_INTERVAL=%d", configured_level7_interval)) begin
            configured_level7_interval = 5;
        end

        if ((configured_level0_interval <= 0) ||
            (configured_level1_interval <= 0) ||
            (configured_level2_interval <= 0) ||
            (configured_level3_interval <= 0) ||
            (configured_level4_interval <= 0) ||
            (configured_level5_interval <= 0) ||
            (configured_level6_interval <= 0) ||
            (configured_level7_interval <= 0)) begin
            $display("ERROR: all LEVEL*_INTERVAL values must be positive");
            $fatal(1);
        end

        level0_interval = configured_level0_interval[INTERVAL_WIDTH-1:0];
        level1_interval = configured_level1_interval[INTERVAL_WIDTH-1:0];
        level2_interval = configured_level2_interval[INTERVAL_WIDTH-1:0];
        level3_interval = configured_level3_interval[INTERVAL_WIDTH-1:0];
        level4_interval = configured_level4_interval[INTERVAL_WIDTH-1:0];
        level5_interval = configured_level5_interval[INTERVAL_WIDTH-1:0];
        level6_interval = configured_level6_interval[INTERVAL_WIDTH-1:0];
        level7_interval = configured_level7_interval[INTERVAL_WIDTH-1:0];

        /*
         * Пороги трёхрежимного управления.
         *
         * Defaults сохраняют старую демонстрационную настройку.
         * Paper/risk-policy режим ниже задаёт coarse-аппроксимацию:
         *   low:    спокойный хвост policy;
         *   medium: активная область;
         *   high:   пиковая область.
         */
        configured_threshold_low_to_medium = 3;
        configured_threshold_medium_to_low = 1;
        configured_threshold_medium_to_high = 6;
        configured_threshold_high_to_medium = 4;

        if (!$value$plusargs("THRESHOLD_LOW_TO_MEDIUM=%d", configured_threshold_low_to_medium)) begin
            configured_threshold_low_to_medium = 3;
        end
        if (!$value$plusargs("THRESHOLD_MEDIUM_TO_LOW=%d", configured_threshold_medium_to_low)) begin
            configured_threshold_medium_to_low = 1;
        end
        if (!$value$plusargs("THRESHOLD_MEDIUM_TO_HIGH=%d", configured_threshold_medium_to_high)) begin
            configured_threshold_medium_to_high = 6;
        end
        if (!$value$plusargs("THRESHOLD_HIGH_TO_MEDIUM=%d", configured_threshold_high_to_medium)) begin
            configured_threshold_high_to_medium = 4;
        end

        if ((configured_threshold_low_to_medium < 0) ||
            (configured_threshold_low_to_medium > 7) ||
            (configured_threshold_medium_to_low < 0) ||
            (configured_threshold_medium_to_low > 7) ||
            (configured_threshold_medium_to_high < 0) ||
            (configured_threshold_medium_to_high > 7) ||
            (configured_threshold_high_to_medium < 0) ||
            (configured_threshold_high_to_medium > 7)) begin
            $display("ERROR: threshold levels must be in range 0..7");
            $fatal(1);
        end

        threshold_low_to_medium = configured_threshold_low_to_medium[LEVEL_WIDTH-1:0];
        threshold_medium_to_low = configured_threshold_medium_to_low[LEVEL_WIDTH-1:0];
        threshold_medium_to_high = configured_threshold_medium_to_high[LEVEL_WIDTH-1:0];
        threshold_high_to_medium = configured_threshold_high_to_medium[LEVEL_WIDTH-1:0];

        /*
         * Интервалы трёх режимов.
         */
        configured_threshold_low_interval = 100;
        configured_threshold_medium_interval = 25;
        configured_threshold_high_interval = 8;

        if (!$value$plusargs("THRESHOLD_LOW_INTERVAL=%d", configured_threshold_low_interval)) begin
            configured_threshold_low_interval = 100;
        end
        if (!$value$plusargs("THRESHOLD_MEDIUM_INTERVAL=%d", configured_threshold_medium_interval)) begin
            configured_threshold_medium_interval = 25;
        end
        if (!$value$plusargs("THRESHOLD_HIGH_INTERVAL=%d", configured_threshold_high_interval)) begin
            configured_threshold_high_interval = 8;
        end

        if ((configured_threshold_low_interval <= 0) ||
            (configured_threshold_medium_interval <= 0) ||
            (configured_threshold_high_interval <= 0)) begin
            $display("ERROR: threshold intervals must be positive");
            $fatal(1);
        end

        threshold_low_interval = configured_threshold_low_interval[INTERVAL_WIDTH-1:0];
        threshold_medium_interval = configured_threshold_medium_interval[INTERVAL_WIDTH-1:0];
        threshold_high_interval = configured_threshold_high_interval[INTERVAL_WIDTH-1:0];

        if (!$value$plusargs("FIXED_INTERVAL=%d", configured_fixed_interval)) begin
            configured_fixed_interval = 80;
        end

        if (configured_fixed_interval <= 0) begin
            $display("ERROR: FIXED_INTERVAL must be positive");
            $display("  actual = %0d", configured_fixed_interval);
            $fatal(1);
        end

        fixed_interval = configured_fixed_interval[INTERVAL_WIDTH-1:0];

        $display("Fixed interval: %0d", configured_fixed_interval);
        $display("Safe interval: %0d", configured_safe_interval);
        $display(
            "Level intervals: L0=%0d L1=%0d L2=%0d L3=%0d L4=%0d L5=%0d L6=%0d L7=%0d",
            configured_level0_interval,
            configured_level1_interval,
            configured_level2_interval,
            configured_level3_interval,
            configured_level4_interval,
            configured_level5_interval,
            configured_level6_interval,
            configured_level7_interval
        );
        $display(
            "Threshold levels: low_to_medium=%0d medium_to_low=%0d medium_to_high=%0d high_to_medium=%0d",
            configured_threshold_low_to_medium,
            configured_threshold_medium_to_low,
            configured_threshold_medium_to_high,
            configured_threshold_high_to_medium
        );
        $display(
            "Threshold intervals: low=%0d medium=%0d high=%0d",
            configured_threshold_low_interval,
            configured_threshold_medium_interval,
            configured_threshold_high_interval
        );

        case (strategy_id)
            0: begin
                strategy_name = "fixed";
                mode = MODE_FIXED;
            end

            1: begin
                strategy_name = "table";
                mode = MODE_TABLE;
            end

            2: begin
                strategy_name = "threshold";
                mode = MODE_THRESHOLD;
            end

            default: begin
                strategy_name = "fixed";
                mode = MODE_FIXED;
            end
        endcase
    end
endtask

task load_fault_events;
    begin
        fault_event_count = 0;
        fault_event_index = 0;

        fault_file = $fopen("tb/fault_events.csv", "r");

        if (fault_file == 0) begin
            $display("ERROR: cannot open tb/fault_events.csv");
            $fatal(1);
        end

        while (!$feof(fault_file)) begin
            fault_read_count = $fscanf(
                fault_file,
                "%d,%d,%h\n",
                fault_time_value,
                fault_addr_value,
                fault_mask_value
            );

            if (fault_read_count == 3) begin
                if (fault_event_count >= MAX_FAULT_EVENTS) begin
                    $display("ERROR: too many fault events");
                    $fatal(1);
                end

                fault_event_time[fault_event_count] = fault_time_value;
                fault_event_addr[fault_event_count] = fault_addr_value;
                if (fault_mask_value == {CODEWORD_WIDTH{1'b0}}) begin
                    $display("ERROR: zero fault mask");
                    $fatal(1);
                end

                fault_event_mask[fault_event_count] = fault_mask_value;

                fault_event_count = fault_event_count + 1;
            end
        end

        $fclose(fault_file);

        $display("Loaded fault events: %0d", fault_event_count);
    end
endtask


task load_control_levels;
    begin
        control_event_count = 0;
        control_event_index = 0;

        control_file = $fopen("tb/control_levels.csv", "r");

        if (control_file == 0) begin
            $display("ERROR: cannot open tb/control_levels.csv");
            $fatal(1);
        end

        while (!$feof(control_file)) begin
            control_read_count = $fscanf(
                control_file,
                "%d,%d\n",
                control_time_value,
                control_level_value
            );

            if (control_read_count == 2) begin
                if (control_event_count >= MAX_CONTROL_EVENTS) begin
                    $display("ERROR: too many control level events");
                    $fatal(1);
                end

                if ((control_level_value < 0) || (control_level_value > 7)) begin
                    $display("ERROR: control level out of range: %0d", control_level_value);
                    $fatal(1);
                end

                control_event_time[control_event_count] = control_time_value;
                control_event_level[control_event_count] = control_level_value;

                control_event_count = control_event_count + 1;
            end
        end

        $fclose(control_file);

        $display("Loaded control level events: %0d", control_event_count);
    end
endtask

task apply_level_schedule;
    input integer cycle_index;
    begin
        ctrl_update = 1'b0;

        /*
         * Управляющие уровни читаются из tb/control_levels.csv.
         * Формат строки: time_cycle,level.
         */
        if (control_event_index < control_event_count) begin
            if (control_event_time[control_event_index] < cycle_index) begin
                $display("ERROR: missed control level event at time %0d",
                         control_event_time[control_event_index]);
                error_count = error_count + 1;
                control_event_index = control_event_index + 1;
            end else if (control_event_time[control_event_index] == cycle_index) begin
                ctrl_level = control_event_level[control_event_index][LEVEL_WIDTH-1:0];
                ctrl_valid = 1'b1;
                ctrl_update = 1'b1;

                control_event_index = control_event_index + 1;

                if ((control_event_index < control_event_count) &&
                    (control_event_time[control_event_index] == cycle_index)) begin
                    $display("ERROR: multiple control level events in one cycle are not supported");
                    $display("  cycle = %0d", cycle_index);
                    error_count = error_count + 1;
                end
            end
        end
    end
endtask

task apply_error_schedule;
    input integer cycle_index;
    begin
        tb_inject_en = 1'b0;
        tb_inject_addr = {ADDR_WIDTH{1'b0}};
        tb_inject_mask = {CODEWORD_WIDTH{1'b0}};

        /*
         * События сбоев читаются из tb/fault_events.csv.
         *
         * Текущая версия поддерживает не более одного события
         * на один такт моделирования. Для кластерных одномоментных
         * событий позже будет добавлен отдельный интерфейс.
         */
        if (fault_event_index < fault_event_count) begin
            if (fault_event_time[fault_event_index] < cycle_index) begin
                $display("ERROR: missed fault event at time %0d", fault_event_time[fault_event_index]);
                error_count = error_count + 1;
                fault_event_index = fault_event_index + 1;
            end else if (fault_event_time[fault_event_index] == cycle_index) begin
                tb_inject_en = 1'b1;
                tb_inject_addr = fault_event_addr[fault_event_index][ADDR_WIDTH-1:0];
                tb_inject_mask = fault_event_mask[fault_event_index];

                injected_event_count = injected_event_count + 1;
                fault_event_index = fault_event_index + 1;

                if ((fault_event_index < fault_event_count) &&
                    (fault_event_time[fault_event_index] == cycle_index)) begin
                    $display("ERROR: multiple fault events in one cycle are not supported yet");
                    $display("  cycle = %0d", cycle_index);
                    error_count = error_count + 1;
                end
            end
        end
    end
endtask

task audit_final_memory;
    integer addr_index;
    begin
        unique_uncorrectable_word_count = 0;

        /*
         * После завершения основного прогона управление памятью
         * возвращается проверочной среде. Мы читаем все слова памяти
         * и считаем число разных адресов, в которых декодер видит
         * неустранимую ошибку.
         */
        tb_mode = 1'b1;
        tb_read_en = 1'b0;
        tb_write_en = 1'b0;
        tb_inject_en = 1'b0;

        for (addr_index = 0; addr_index < DEPTH; addr_index = addr_index + 1) begin
            read_memory_word(addr_index[ADDR_WIDTH-1:0]);

            if (checked_uncorrectable) begin
                unique_uncorrectable_word_count = unique_uncorrectable_word_count + 1;
            end
        end
    end
endtask

task capture_metrics_snapshot;
    begin
        snap_total_cycle_count = total_cycle_count;
        snap_scrub_cycle_count = scrub_cycle_count;
        snap_memory_read_count = memory_read_count;
        snap_memory_write_count = memory_write_count;
        snap_corrected_error_count = corrected_error_count;
        snap_uncorrectable_error_count = uncorrectable_error_count;
        snap_interval_switch_count = interval_switch_count;
        snap_safe_mode_entry_count = safe_mode_entry_count;
        snap_safe_mode_cycle_count = safe_mode_cycle_count;
        snap_scrub_active_cycle_count = scrub_active_cycle_count;
        snap_memory_busy_cycle_count = memory_busy_cycle_count;
    end
endtask

task trace_execution_event;
    begin
        if (trace_execution != 0) begin
            if (scrub_cycle_count != previous_trace_scrub_cycle_count) begin
                trace_file = $fopen(trace_output_path, "a");

                if (trace_file == 0) begin
                    $display("ERROR: cannot open execution trace file");
                    $display("  path = %0s", trace_output_path);
                    error_count = error_count + 1;
                end else begin
                    $fdisplay(
                        trace_file,
                        "%0s,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",
                        strategy_name,
                        sim_cycle,
                        scrub_cycle_count,
                        selected_interval,
                        effective_wait_interval,
                        last_pass_duration,
                        current_level,
                        threshold_state,
                        safe_mode_active,
                        control_age
                    );

                    $fclose(trace_file);
                end

                previous_trace_scrub_cycle_count = scrub_cycle_count;
            end
        end
    end
endtask

task write_results;
    begin
        if (snap_total_cycle_count != 0) begin
            busy_per_mille = (snap_memory_busy_cycle_count * 1000) / snap_total_cycle_count;
            scrub_per_mille = (snap_scrub_active_cycle_count * 1000) / snap_total_cycle_count;
            safe_per_mille = (snap_safe_mode_cycle_count * 1000) / snap_total_cycle_count;
        end else begin
            busy_per_mille = 0;
            scrub_per_mille = 0;
            safe_per_mille = 0;
        end

        csv_file = $fopen("results/tables/strategy_comparison.csv", "a");

        if (csv_file == 0) begin
            $display("ERROR: cannot open results/tables/strategy_comparison.csv");
            error_count = error_count + 1;
        end else begin
            $fdisplay(
                csv_file,
                "%0s,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",
                strategy_name,
                snap_total_cycle_count,
                snap_scrub_cycle_count,
                snap_memory_read_count,
                snap_memory_write_count,
                snap_corrected_error_count,
                snap_uncorrectable_error_count,
                unique_uncorrectable_word_count,
                snap_interval_switch_count,
                snap_safe_mode_entry_count,
                snap_safe_mode_cycle_count,
                snap_scrub_active_cycle_count,
                snap_memory_busy_cycle_count,
                scrub_per_mille,
                busy_per_mille,
                safe_per_mille
            );

            $fclose(csv_file);
        end

        $display("STRATEGY RESULT: %0s", strategy_name);
        $display("  total_cycle_count         = %0d", snap_total_cycle_count);
        $display("  scrub_cycle_count         = %0d", snap_scrub_cycle_count);
        $display("  memory_read_count         = %0d", snap_memory_read_count);
        $display("  memory_write_count        = %0d", snap_memory_write_count);
        $display("  corrected_error_count     = %0d", snap_corrected_error_count);
        $display("  uncorrectable_detections  = %0d", snap_uncorrectable_error_count);
        $display("  unique_uncorrectable_words = %0d", unique_uncorrectable_word_count);
        $display("  interval_switch_count     = %0d", snap_interval_switch_count);
        $display("  memory_busy_cycle_count   = %0d", snap_memory_busy_cycle_count);
        $display("  busy_per_mille            = %0d", busy_per_mille);
    end
endtask

initial begin
    dump_vcd = 0;

    if (!$value$plusargs("DUMP_VCD=%d", dump_vcd)) begin
        dump_vcd = 0;
    end

    if (dump_vcd != 0) begin
        $dumpfile("results/logs/strategy_comparison.vcd");
        $dumpvars(0, tb_strategy_comparison);
    end

    error_count = 0;
    injected_event_count = 0;

    trace_execution = 0;
    trace_output_path = "results/tables/strategy_execution_trace.csv";
    previous_trace_scrub_cycle_count = 0;

    if (!$value$plusargs("TRACE_EXECUTION=%d", trace_execution)) begin
        trace_execution = 0;
    end

    if (!$value$plusargs("TRACE_OUTPUT=%s", trace_output_path)) begin
        trace_output_path = "results/tables/strategy_execution_trace.csv";
    end

    rst = 1'b1;
    enable = 1'b0;

    ctrl_level = 3'd0;
    ctrl_valid = 1'b0;
    ctrl_update = 1'b0;

    tb_mode = 1'b1;

    tb_read_en = 1'b0;
    tb_read_addr = {ADDR_WIDTH{1'b0}};

    tb_write_en = 1'b0;
    tb_write_addr = {ADDR_WIDTH{1'b0}};
    tb_write_data = {CODEWORD_WIDTH{1'b0}};

    tb_inject_en = 1'b0;
    tb_inject_addr = {ADDR_WIDTH{1'b0}};
    tb_inject_mask = {CODEWORD_WIDTH{1'b0}};

    encoder_data_in = 32'd0;

    configure_run_length();
    configure_strategy();
    load_fault_events();
    load_control_levels();

    repeat (3) @(posedge clk);
    #1;

    /*
     * Начальная запись одинакового содержимого памяти.
     */
    for (i = 0; i < DEPTH; i = i + 1) begin
        write_memory_word(i[ADDR_WIDTH-1:0], 32'h4000_0000 + i);
    end

    /*
     * Передаём память контроллеру.
     */
    tb_mode = 1'b0;

    rst = 1'b0;
    enable = 1'b1;
    previous_trace_scrub_cycle_count = 0;
    /*
     * Основной цикл моделирования.
     */
    for (sim_cycle = 0; sim_cycle < total_run_cycles; sim_cycle = sim_cycle + 1) begin
        apply_level_schedule(sim_cycle);
        apply_error_schedule(sim_cycle);

        @(posedge clk);
        #1;
        trace_execution_event();
        ctrl_update = 1'b0;
        tb_inject_mask = {CODEWORD_WIDTH{1'b0}};
    end

    /*
     * Сохраняем снимок метрик сразу после основного окна моделирования.
     * Дальнейший аудит памяти не должен изменять численные метрики стратегии.
     */
    capture_metrics_snapshot();

    enable = 1'b0;

    repeat (3) @(posedge clk);
    #1;

    /*
     * Итоговая проверка памяти:
     * считаем число разных слов, оставшихся в неустранимом состоянии.
     */
    audit_final_memory();

    if (control_event_index !== control_event_count) begin
        $display("ERROR: not all control level events were applied");
        $display("  expected = %0d", control_event_count);
        $display("  actual   = %0d", control_event_index);
        error_count = error_count + 1;
    end

    if (injected_event_count !== fault_event_count) begin
        $display("ERROR: wrong injected_event_count");
        $display("  expected = %0d", fault_event_count);
        $display("  actual   = %0d", injected_event_count);
        error_count = error_count + 1;
    end

    if (safe_mode_entry_count !== 32'd0) begin
        $display("ERROR: safe mode must not be entered in strategy comparison");
        $display("  safe_mode_entry_count = %0d", safe_mode_entry_count);
        error_count = error_count + 1;
    end

    write_results();

    if (error_count == 0) begin
        $display("Strategy comparison run passed for strategy %0s.", strategy_name);
    end else begin
        $display("Strategy comparison run failed for strategy %0s. Errors: %0d", strategy_name, error_count);
        $fatal(1);
    end

    $finish;
end

endmodule
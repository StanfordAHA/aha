from pathlib import Path
import os
import subprocess
import sys
import copy
import re

pattern_usage = re.compile(r"^(PE|MEM|Pond|IO|Reg)s:\s(\d+)")
pattern_critical_path = re.compile(r"^\s*Critical Path: (\d+)")
pattern_cycle = re.compile(r"^\[.+\]\sIt\stakes\s(\d+\.\d*)\sns\stotal\stime\sto\srun\skernel")


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app")
    parser.set_defaults(dispatch=dispatch)


def get_map_results(aha_map_log_path):
    default_str = "NA"
    map_results = {}
    map_results["PE"] = default_str
    map_results["MEM"] = default_str
    map_results["Pond"] = default_str
    map_results["IO"] = default_str
    map_results["Reg"] = default_str
    if not os.path.exists(aha_map_log_path):
        return map_results
    with open(aha_map_log_path, "r") as f:
        current_items, total_items = 0, len(map_results)
        line = f.readline()
        while line and current_items < total_items:
            m = pattern_usage.match(line)
            if m:
                current_items += 1
                map_results[m.group(1)] = m.group(2)
            line = f.readline()
    return map_results


def get_sta_results(aha_sta_log_path):
    default_str = "NA"
    sta_results = {}
    sta_results["Critical Path (ps)"] = default_str
    sta_results["Frequency (MHz)"] = default_str
    if not os.path.exists(aha_sta_log_path):
        return sta_results
    with open(aha_sta_log_path, "r") as f:
        current_items, total_items = 0, len(sta_results)
        line = f.readline()
        while line and current_items < total_items:
            m = pattern_critical_path.match(line)
            if m:
                current_items += 1
                sta_results["Critical Path (ps)"] = m.group(1)
            line = f.readline()
    if sta_results["Critical Path (ps)"] == "NA":
        sta_results["Frequency (MHz)"] = "NA"
    else:
        freq = 1000000 / float(sta_results["Critical Path (ps)"])
        sta_results["Frequency (MHz)"] = "{:.2f}".format(freq)
    return sta_results


def get_glb_results(aha_glb_log_path):
    default_str = "NA"
    glb_results = {}
    glb_results["Simultaion Cycles"] = default_str
    if not os.path.exists(aha_glb_log_path):
        return glb_results
    with open(aha_glb_log_path, "r") as f:
        current_items, total_items = 0, len(glb_results)
        line = f.readline()
        while line and current_items < total_items:
            m = pattern_cycle.match(line)
            if m:
                current_items += 1
                glb_results["Simultaion Cycles"] = m.group(1)
            line = f.readline()
    return glb_results


def print_report_items(report_items):
    var_len = 20
    print("=== AHA flow summary ===")
    for key, val in report_items.items():
        print("{0:{1}} : {2}".format(key, var_len, val))


def get_array_dimension():
    results = {}
    results["Array_Width"] = 0
    results["Array_Height"] = 0
    results["Total_PE"] = 0
    results["Total_MemCore"] = 0
    # use grep to pre-parse the verilog file
    temp_file = "/aha/garnet/grep_tiles.txt"
    with open(temp_file, "w") as f_temp:
        cmd = ["grep", "^Tile", "/aha/garnet/garnet.v"]
        subprocess.check_call(cmd, stdout=f_temp)
    # parse the grep results
    pattern = re.compile(r"^Tile_(PE|MemCore)\sTile_X(\w+)_Y(\w+)\s\(")
    with open(temp_file, "r") as f_temp:
        line = f_temp.readline()
        while line:
            m = pattern.match(line)
            if m:
                tile = m.group(1)
                x_dim = int(m.group(2), 16)
                y_dim = int(m.group(3), 16)
                if tile == "PE":
                    results["Total_PE"] += 1
                elif tile == "MemCore":
                    results["Total_MemCore"] += 1
                results["Array_Width"] = max(x_dim + 1, results["Array_Width"])
                # on vertical direction, we have IO tile at top, so don't need +1
                results["Array_Height"] = max(y_dim, results["Array_Height"])
            line = f_temp.readline()
    subprocess.check_call(["rm", "-f", temp_file])
    return results


def get_num_tracks():
    results = {}
    results["#Tracks"] = 0
    # use grep to pre-parse the verilog file
    temp_file = "/aha/garnet/grep_tiles.txt"
    with open(temp_file, "w") as f_temp:
        cmd = ["grep", "^module SB_ID", "/aha/garnet/garnet.v"]
        subprocess.check_call(cmd, stdout=f_temp)
    # parse the grep results
    pattern = re.compile(r"^module\sSB_ID\d+_(\d+)TRACKS")
    with open(temp_file, "r") as f_temp:
        line = f_temp.readline()
        while line:
            m = pattern.match(line)
            if m:
                results["#Tracks"] = int(m.group(1))
                break
            line = f_temp.readline()
    subprocess.check_call(["rm", "-f", temp_file])
    return results


def get_absolute_time(report_items):
    results = {}
    results["Execution Time (us)"] = "NA"
    try:
        cycle = float(report_items["Simultaion Cycles"])
        period = float(report_items["Critical Path (ps)"])
    except ValueError:
        return results
    exe_time = cycle * period / 1000000
    results["Execution Time (us)"] = "{:.2f}".format(exe_time)
    return results


def dump_to_csv(report_items):
    csv_path = "/aha/cgra_dse/experiment_db.csv"
    keys = []
    vals = []
    for key, val in report_items.items():
        keys.append(f"{key}")
        vals.append(f"{val}")
    key_str = ",".join(keys) + "\n"
    val_str = ",".join(vals) + "\n"
    write_header = False
    if not os.path.exists(csv_path):
        write_header = True
    with open(csv_path, "a") as f:
        if write_header:
            f.write(key_str)
        f.write(val_str)


def dispatch(args, extra_args=None):
    args.app = Path(args.app)
    app_dir = Path(f"{args.aha_dir}/Halide-to-Hardware/apps/hardware_benchmarks/{args.app}")

    # log file locations
    aha_halide_log = app_dir / Path("log/aha_halide.log")
    aha_map_log = app_dir / Path("log/aha_map.log")
    aha_sta_log = app_dir / Path("log/aha_sta.log")
    aha_glb_log = app_dir / Path("log/aha_glb.log")

    # variable to store all results
    report_items = {}
    report_items["Application"] = args.app

    # parse the log files
    report_items.update(get_array_dimension())
    report_items.update(get_num_tracks())
    report_items.update(get_map_results(aha_map_log))
    report_items.update(get_sta_results(aha_sta_log))
    report_items.update(get_glb_results(aha_glb_log))
    report_items.update(get_absolute_time(report_items))

    # print the results
    print_report_items(report_items)
    dump_to_csv(report_items)


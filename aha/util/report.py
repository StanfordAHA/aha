from pathlib import Path
import os
import subprocess
import sys
import copy
import re
import pandas as pd
from datetime import datetime



def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app")
    parser.add_argument("--tag", type=str, default="")
    parser.add_argument("--dump-report", action="store_true")
    parser.add_argument("--dump-report-location", type=str, default="/aha/garnet/aha_report.csv")
    parser.set_defaults(dispatch=dispatch)


def get_map_results(aha_map_log_path):
    pattern = re.compile(r"^(PE|MEM|Pond|IO|Reg)s:\s(\d+)")
    default_str = "NA"
    results = {}
    results["PE"] = default_str
    results["MEM"] = default_str
    results["Pond"] = default_str
    results["IO"] = default_str
    results["Reg"] = default_str
    if not os.path.exists(aha_map_log_path):
        return results
    with open(aha_map_log_path, "r") as f:
        current_items, total_items = 0, len(results)
        line = f.readline()
        while line and current_items < total_items:
            m = pattern.match(line)
            if m:
                current_items += 1
                results[m.group(1)] = m.group(2)
            line = f.readline()
    return results


def get_sta_results(aha_sta_log_path):
    pattern = re.compile(r"^\s*Critical Path: (\d+)")
    default_str = "NA"
    results = {}
    results["Critical_Path_ps"] = default_str
    results["Frequency_MHz"] = default_str
    if not os.path.exists(aha_sta_log_path):
        return results
    with open(aha_sta_log_path, "r") as f:
        current_items, total_items = 0, len(results)
        line = f.readline()
        while line and current_items < total_items:
            m = pattern.match(line)
            if m:
                current_items += 1
                results["Critical_Path_ps"] = m.group(1)
            line = f.readline()
    if results["Critical_Path_ps"] == "NA":
        results["Frequency_MHz"] = "NA"
    else:
        freq = 1000000 / float(results["Critical_Path_ps"])
        results["Frequency_MHz"] = "{:.2f}".format(freq)
    return results


def get_glb_results(aha_glb_log_path):
    pattern = re.compile(r"^\[.+\]\sIt\stakes\s(\d+\.\d*)\sns\stotal\stime\sto\srun\skernel")
    default_str = "NA"
    results = {}
    results["Simultaion_Cycles"] = default_str
    if not os.path.exists(aha_glb_log_path):
        return results
    with open(aha_glb_log_path, "r") as f:
        current_items, total_items = 0, len(results)
        line = f.readline()
        while line and current_items < total_items:
            m = pattern.match(line)
            if m:
                current_items += 1
                results["Simultaion_Cycles"] = m.group(1)
            line = f.readline()
    return results


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
    results["Num_Tracks"] = 0
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
                results["Num_Tracks"] = int(m.group(1))
                break
            line = f_temp.readline()
    subprocess.check_call(["rm", "-f", temp_file])
    return results


def get_absolute_time(report_items):
    results = {}
    results["Execution_Time_us"] = "NA"
    try:
        cycle = float(report_items["Simultaion_Cycles"])
        period = float(report_items["Critical_Path_ps"])
    except ValueError:
        return results
    exe_time = cycle * period / 1000000
    results["Execution_Time_us"] = "{:.2f}".format(exe_time)
    return results


def dump_to_csv(report_items, csv_path):
    if not os.path.exists(csv_path):
        df = pd.DataFrame([{}])
    else:
        df = pd.read_csv(csv_path)
    df_new = pd.DataFrame([report_items])
    df = pd.concat([df, df_new], ignore_index=True)
    df.to_csv(csv_path, index=False)


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
    report_items["Tag"] = args.tag

    # parse the log files
    report_items.update(get_array_dimension())
    report_items.update(get_num_tracks())
    report_items.update(get_map_results(aha_map_log))
    report_items.update(get_sta_results(aha_sta_log))
    report_items.update(get_glb_results(aha_glb_log))
    report_items.update(get_absolute_time(report_items))

    # print the results
    report_items["Time_Stamp"] = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    print_report_items(report_items)
    if args.dump_report:
        dump_to_csv(report_items, csv_path=args.dump_report_location)


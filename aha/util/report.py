from pathlib import Path
import os
import subprocess
import sys
import copy
import re

pattern_usage = re.compile(r"^(PE|MEM|Pond|IO|Reg)s:\s(\d+)")
pattern_critical_path = re.compile(r"^\s*Critical Path: (\d+.?\d*)")
pattern_cycle = re.compile(r"^\[.+\]\sIt\stakes\s(\d+\.\d*)\sns\stotal\stime\sto\srun\skernel")

def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem, add_help=False)
    parser.add_argument("app")
    parser.set_defaults(dispatch=dispatch)


def get_map_results(aha_map_log_path):
    default_str = "N/A - Have you run aha map with --log option enabled?"
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
    default_str = "N/A - Have you run aha sta with --log option enabled?"
    sta_results = {}
    sta_results["Critical Path (ps)"] = default_str
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
    return sta_results


def get_glb_results(aha_glb_log_path):
    default_str = "N/A - Have you run aha glb with --log option enabled?"
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


def print_report_items(app, report_items):
    var_len = 20
    print("=== AHA flow summary ===")
    print("{0:{1}} : {2}".format("Application Name", var_len, app))
    for key, val in report_items.items():
        print("{0:{1}} : {2}".format(key, var_len, val))


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

    # parse the log files
    report_items.update(get_map_results(aha_map_log))
    report_items.update(get_sta_results(aha_sta_log))
    report_items.update(get_glb_results(aha_glb_log))

    # print the results
    print_report_items(args.app, report_items)

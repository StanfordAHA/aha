"""`aha pnr --rv-balance N`: latency matching for dense ready-valid apps.

In dense RV every register is a 2-deep FIFO and a fanout is a lazy fork (a token
leaves only when every branch takes it). When a fork's branches rejoin at a PE with
different stage counts, the short branch fills and the fork stalls, so the join runs
below one token per cycle (conv_3_3 3/4, harris_color about 1/9 of the static rate).
Static PnR delay-matches its branches; RV maps with MATCH_BRANCH_DELAY=0, so nothing
balances them.

After the first PnR this models the routed design (garnet
mflowgen/common/application/rv_throughput.py), latency-matches every PE join with the
fewest pass-through registers (min_register_plan: an LP; the padded inputs of one
driver share one chain, and a PE may start late to move padding off shared edges),
inserts them (hooks/rv_balance_branches.py --share: coreir.reg / corebit.reg with
extra_data 0, so data is unchanged), pins every block
and netlist register where it was (manual.place + MANUAL_PATH_BALANCE_PLACER) and runs
PnR again with cyclone's register-aware route search (CYCLONE_REG_SEARCH=1; the stock
search cannot route long padding chains); at most N rounds, until no join is mismatched. Needs PnR without
pipelining (no EXHAUSTIVE_PIPE / POST_PNR_ITR): route hops are then wires, so a
padding register adds exactly one stage. Notes: garnet mflowgen/CLAUDE.md "RV branch
balancing".
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

MARK = "rv_balance"   # design_top metadata key the hook writes


def _balanced(top_json):
    d = json.load(open(top_json))
    top = d["top"].split(".", 1)[1]
    return bool((d["namespaces"]["global"]["modules"][top].get("metadata") or {}).get(MARK))


def _padding_registers(bin_dir):
    """Padding registers in the netlist the last PnR placed (the hook's count)."""
    d = json.load(open(bin_dir / "design_top.json"))
    top = d["top"].split(".", 1)[1]
    meta = (d["namespaces"]["global"]["modules"][top].get("metadata") or {}).get(MARK) or {}
    return meta.get("registers", 0)


def check_env(env, extra_args):
    """Refuse the combinations the plan does not model."""
    if env.get("DENSE_READY_VALID") != "1":
        sys.exit("*** --rv-balance needs DENSE_READY_VALID=1 (static PnR balances branches itself)")
    for v in ("EXHAUSTIVE_PIPE", "POST_PNR_ITR"):
        if env.get(v, "0") not in ("", "0"):
            sys.exit(f"*** --rv-balance assumes PnR without pipelining: unset {v}")
    if "--daemon" in extra_args:
        sys.exit("*** --rv-balance runs PnR more than once: not with --daemon")


def restore(app_dir):
    """Start from the app's own netlist: a design_top.json an earlier --rv-balance run
    padded goes back to the hook's saved input, and no stale manual.place pins it."""
    bin_dir = app_dir / "bin"
    top, orig = bin_dir / "design_top.json", bin_dir / "design_top.pre_rv_balance.json"
    if orig.exists() and _balanced(top):
        shutil.copy(orig, top)
        print(f"--- rv-balance: restored {top} from {orig.name}")
    for p in (app_dir / "manual.place", bin_dir / "manual.place"):
        p.unlink(missing_ok=True)


def balance(app_dir, garnet_dir, rounds, run_pnr, env):
    """Rounds of model -> pad -> pinned PnR (run_pnr(env)) until no PE join is
    mismatched. Writes bin/rv_balance_plan.json ({"<instance>.<port>": registers}, on
    the app's own netlist) and bin/rv_balance_log.json. -> the log"""
    application = Path(garnet_dir) / "mflowgen" / "common" / "application"
    sys.path.insert(0, str(application))
    import rv_throughput as rt
    bin_dir = app_dir / "bin"
    if (bin_dir / "PE_fifos_bypass_config.json").exists():
        print("*** rv-balance WARNING: bin/PE_fifos_bypass_config.json exists; the model "
              "assumes every PE FIFO is present", flush=True)
    hook = application / "hooks" / "rv_balance_branches.py"
    plan_file = bin_dir / "rv_balance_plan.json"
    plan, log = {}, []
    for rnd in range(rounds + 1):
        m = rt.model_of(bin_dir)
        rate, _ = m.run(6000, 1500)
        early = [d for _, d in rt.mismatches(m) if d > 0]
        regs = _padding_registers(bin_dir)
        log.append({"round": rnd, "modelled_rate": round(rate, 4), "early_inputs": len(early),
                    "early_stages": sum(early), "padding_registers": regs})
        print(f"--- [{time.strftime('%H:%M:%S')}] rv-balance round {rnd}: modelled rate {rate:.3f}, "
              f"{len(early)} early PE inputs ({sum(early)} stages), "
              f"{regs} padding registers", flush=True)
        if not early or rnd == rounds:
            break
        lp = hasattr(rt, "min_register_plan")   # older garnet: a chain per padded input
        more = rt.min_register_plan(m) if lp else rt.latency_match_plan(m)
        for key, k in rt.plan_by_instance(m, more).items():
            plan[key] = plan.get(key, 0) + k
        plan_file.write_text(json.dumps(plan, indent=1, sort_keys=True))
        subprocess.check_call([sys.executable, str(hook), str(bin_dir), "--plan", str(plan_file),
                               "--pe-stages", "0", "--margin", "0"] + (["--share"] if lp else []),
                              env=env)
        # every block and netlist register stays put; only the new padding registers move
        with open(app_dir / "manual.place", "w") as f:
            for blk, (x, y) in sorted(rt.placement_of(bin_dir).items()):
                f.write(f"{blk} {x} {y}\n")
        # padding chains need the register-aware route search (cgra_pnr thesis, route.cc)
        run_pnr(dict(env, MANUAL_PATH_BALANCE_PLACER="1",
                     CYCLONE_REG_SEARCH=env.get("CYCLONE_REG_SEARCH", "1")))
    for p in (app_dir / "manual.place", bin_dir / "manual.place"):
        p.unlink(missing_ok=True)
    json.dump(log, open(bin_dir / "rv_balance_log.json", "w"), indent=1)
    if log[-1]["early_inputs"]:
        print(f"*** rv-balance: {log[-1]['early_inputs']} PE inputs still early after {rounds} "
              f"round(s)", flush=True)
    return log

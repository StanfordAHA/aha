"""End to end at CGRA data widths other than 16: fabric from a lake spec, then
`aha map` / `aha pnr` / `aha test`, bit-accurate against the Halide gold.

Opt-in and slow (~1 h): set AHA_DATA_WIDTH_E2E=1. It runs in the aha tree given by
AHA_DATA_WIDTH_E2E_DIR (default: this repo) and WRITES to it: garnet.v, the GLB
headers and the apps' bin/ directories. Use a private copy of the tree, not one other
people simulate against, e.g.

    AHA_DATA_WIDTH_E2E=1 AHA_DATA_WIDTH_E2E_DIR=/path/to/private/aha \\
        python -m pytest -v tests/test_data_width_e2e.py

Each case covers a piece of the width work (garnet mflowgen/CLAUDE.md "Fabric data
width follows the spec"): the width comes only from the spec; the compiler reads it
from the spec's lake collateral. The `thesis` cases build the thesis fabrics
(`garnet.py --thesis static|rv`, garnet mflowgen/CLAUDE.md "Thesis fabrics"): dw-bit
tracks with no end-of-stream bit, a spec pond at the fabric width, and RV placed and
routed without EXHAUSTIVE_PIPE (aha pnr balances the branches).
"""
import json
import os
import shlex
import subprocess
from pathlib import Path

import pytest

AHA = Path(os.environ.get("AHA_DATA_WIDTH_E2E_DIR", Path(__file__).resolve().parent.parent))
pytestmark = pytest.mark.skipif(os.environ.get("AHA_DATA_WIDTH_E2E") != "1",
                                reason="opt-in: AHA_DATA_WIDTH_E2E=1 (slow, writes to the aha tree)")

# app, data width, runtime mode, fetch width, array width x height, fabric, what it guards
CASES = [
    ("tests/arith", 32, "static", 4, 4, 4, "stock", "PE + IO at 32 bits"),
    ("tests/arith", 32, "rv", 4, 4, 4, "stock", "ready-valid fabric at 32 bits"),
    ("tests/arith", 64, "rv", 2, 4, 4, "stock", "64 bits (fw2: dw64 x fw4 has no SRAM macro)"),
    ("tests/rom", 32, "static", 4, 4, 4, "stock", "Halide ROM at the CGRA width (1867c7a36)"),
    ("tests/uminmax", 32, "static", 4, 4, 4, "stock", "coreir commonlib min/max at any width (f32ab1b9)"),
    ("tests/multmiddle", 32, "static", 4, 4, 4, "stock", "mult_middle only at 16 (Halide 176cfdc04)"),
    ("tests/conv_3_3", 32, "static", 2, 4, 8, "stock", "static fw=2 line buffers (clockwork 9fdfe6bf)"),
    ("apps/scalar_reduction", 32, "static", 4, 16, 8, "stock", "PE-tile pond at 32 bits + archipelago pond port"),
    ("tests/arith", 32, "static", 4, 4, 4, "thesis", "thesis static fabric: PE + IO on 32-bit tracks"),
    ("tests/arith", 32, "rv", 4, 4, 4, "thesis", "thesis RV fabric at 32 bits (no EOS bit)"),
    ("tests/arith", 64, "static", 2, 4, 4, "thesis", "thesis static fabric at 64 bits"),
    ("tests/arith", 64, "rv", 2, 4, 4, "thesis", "thesis RV fabric at 64 bits"),
    ("tests/conv_3_3", 32, "static", 4, 4, 8, "thesis", "thesis MEM line buffers at 32 bits (static)"),
    ("tests/conv_3_3", 32, "rv", 4, 4, 8, "thesis", "thesis MEM line buffers at 32 bits (RV, balanced)"),
    ("apps/scalar_reduction", 32, "static", 4, 16, 8, "thesis", "thesis static spec pond at 32 bits"),
    # (scalar_reduction has only a static hack_design_top.py rewrite: no RV case at any width)
    ("tests/matmul_bounded", 8, "rv", 4, 16, 16, "thesis", "thesis RV pond accumulation at 8 bits"),
    ("tests/matmul_bounded", 32, "rv", 4, 16, 16, "thesis", "thesis RV pond accumulation at 32 bits"),
    ("tests/matmul_bounded", 64, "rv", 2, 16, 16, "thesis", "thesis RV pond accumulation at 64 bits"),
    ("tests/conv_3_3_u8", 8, "static", 4, 4, 8, "thesis", "thesis static fabric at 8 bits (uint8 line buffers)"),
    ("tests/conv_3_3_u8", 8, "rv", 4, 4, 8, "thesis", "thesis RV fabric at 8 bits (uint8 line buffers)"),
]

SHELL_SETUP = ("set +u; source /cad/modules/tcl/init/bash; module load base; module load xcelium; "
               "source /aha/bin/activate; ")


def _bash(cmd, env, log):
    with open(log, "w") as f:
        return subprocess.run(["bash", "-c", SHELL_SETUP + cmd], env=env, stdout=f, stderr=subprocess.STDOUT).returncode


def _base_env(app, spec, mode, pond_spec=None):
    env = {k: v for k, v in os.environ.items()
           if k not in ("DENSE_READY_VALID", "PIPELINED", "MATCH_BRANCH_DELAY", "EXHAUSTIVE_PIPE",
                        "CGRA_DATA_WIDTH", "LAKE_COLLATERAL_JSON_MEM", "LAKE_COLLATERAL_JSON_REGFILE",
                        "LAKE_POND_SPEC_CONFIG", "USE_NON_SPLIT_FIFOS", "RV_FLUSH_FIRST")}
    env.update(GARNET_HOME=str(AHA / "garnet"), TOOL="XCELIUM", LAKE_SPEC_CONFIG=spec, LAKE_SPEC_MODE=mode,
               PYTHONPATH=":".join(str(AHA / p) for p in ("", "garnet", "MetaMapper", "archipelago", "lassen")))
    if pond_spec:
        # The thesis fabrics always build a spec pond; aha map makes its collateral from this
        # (RV pond iff LAKE_SPEC_MODE=rv), at the fabric width
        env["LAKE_POND_SPEC_CONFIG"] = pond_spec
    else:
        env["USE_NON_SPLIT_FIFOS"] = "1"
    params = json.load(open(AHA / "aha/util/application_parameters.json")).get(app, {}).get("default", {})
    env.update({k: str(v) for k, v in params.items()})
    return env


def _built(width, height, dw, fw, mode, fabric):
    tag = AHA / "garnet" / ".e2e_built_tag"
    want = f"{width} {height} {dw} {fw} {mode} {fabric}"
    return tag, want, tag.exists() and tag.read_text() == want and (AHA / "garnet" / "garnet.v").exists()


@pytest.mark.parametrize("app,dw,mode,fw,width,height,fabric,guards", CASES,
                         ids=[f"{c[6]}-{c[0].split('/')[1]}-dw{c[1]}-{c[2]}-fw{c[3]}" for c in CASES])
def test_app_bit_accurate(tmp_path, app, dw, mode, fw, width, height, fabric, guards):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(dict(data_width=dw, in_ports=2, out_ports=2, storage_capacity=8192,
                                    vec_width=fw)))
    if fabric == "thesis":
        pond = tmp_path / "pond_spec.json"
        pond.write_text(json.dumps(dict(data_width=dw)))
        flags = (f"--thesis {mode} --use_sim_sram --glb_tile_mem_size 128 --lake-spec-config {spec} "
                 f"--lake-pond-spec-config {pond}")
        env = _base_env(app, str(spec), mode, pond_spec=str(pond))
    else:
        flags = (f"--use_sim_sram --glb_tile_mem_size 128 --lake-spec-config {spec} --lake-spec-mode {mode} "
                 "--use-non-split-fifos")
        env = _base_env(app, str(spec), mode)
    app_dir = AHA / "Halide-to-Hardware/apps/hardware_benchmarks" / app

    # Fabric (reused while the configuration is the same)
    tag, want, ok = _built(width, height, dw, fw, mode, fabric)
    if not ok:
        tag.unlink(missing_ok=True)
        for attempt in range(3):  # garnet.py has a flaky native crash
            rc = _bash(f"cd {AHA / 'garnet'} && rm -f garnet.v && python garnet.py --width {width} "
                       f"--height {height} --verilog {flags}", env, tmp_path / "garnet.log")
            if rc == 0 and (AHA / "garnet" / "garnet.v").exists():
                tag.write_text(want)
                break
        assert tag.exists(), (tmp_path / "garnet.log").read_text()[-3000:]

    # Compile: aha map generates the MEM collateral from LAKE_SPEC_CONFIG (data_width included)
    map_env = dict(env)
    if mode == "rv":
        map_env.update(DENSE_READY_VALID="1", PIPELINED="0", MATCH_BRANCH_DELAY="0")
    _bash(f"cd {app_dir} && make clean", map_env, tmp_path / "clean.log")
    assert _bash(f"cd {AHA} && aha --dir {AHA} map {app}", map_env, tmp_path / "map.log") == 0, \
        (tmp_path / "map.log").read_text()[-3000:]
    coll = app_dir / "bin" / "lake_collateral_mem.json"
    assert json.loads(coll.read_text())["data_width"] == dw

    run_env = dict(env, LAKE_COLLATERAL_JSON_MEM=str(coll))
    pond_coll = app_dir / "bin" / "lake_collateral_regfile.json"
    if fabric == "thesis":
        assert json.loads(pond_coll.read_text())["data_width"] == dw
        run_env["LAKE_COLLATERAL_JSON_REGFILE"] = str(pond_coll)
    if mode == "rv":
        # The thesis RV flow places and routes without PnR pipelining (aha pnr balances)
        run_env.update(DENSE_READY_VALID="1", **({} if fabric == "thesis" else {"EXHAUSTIVE_PIPE": "1"}))
    assert _bash(f"cd {AHA} && aha --dir {AHA} pnr {app} --width {width} --height {height} {flags}",
                 run_env, tmp_path / "pnr.log") == 0, (tmp_path / "pnr.log").read_text()[-3000:]
    rc = _bash(f"cd {AHA} && timeout 3600 aha --dir {AHA} test {app}", run_env, tmp_path / "test.log")
    log = (tmp_path / "test.log").read_text()
    assert rc == 0 and "comparison passed" in log, f"{guards}\n" + log[-3000:]

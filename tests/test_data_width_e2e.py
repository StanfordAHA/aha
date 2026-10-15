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
from the spec's lake collateral.
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

# app, data width, runtime mode, fetch width, array width x height, what it guards
CASES = [
    ("tests/arith", 32, "static", 4, 4, 4, "PE + IO at 32 bits"),
    ("tests/arith", 32, "rv", 4, 4, 4, "ready-valid fabric at 32 bits"),
    ("tests/arith", 64, "rv", 2, 4, 4, "64 bits (fw2: dw64 x fw4 has no SRAM macro)"),
    ("tests/rom", 32, "static", 4, 4, 4, "Halide ROM at the CGRA width (1867c7a36)"),
    ("tests/uminmax", 32, "static", 4, 4, 4, "coreir commonlib min/max at any width (f32ab1b9)"),
    ("tests/multmiddle", 32, "static", 4, 4, 4, "mult_middle only at 16 (Halide 176cfdc04)"),
    ("tests/conv_3_3", 32, "static", 2, 4, 8, "static fw=2 line buffers (clockwork 9fdfe6bf)"),
    ("apps/scalar_reduction", 32, "static", 4, 16, 8, "PE-tile pond at 32 bits + archipelago pond port"),
]

SHELL_SETUP = ("set +u; source /cad/modules/tcl/init/bash; module load base; module load xcelium; "
               "source /aha/bin/activate; ")


def _bash(cmd, env, log):
    with open(log, "w") as f:
        return subprocess.run(["bash", "-c", SHELL_SETUP + cmd], env=env, stdout=f, stderr=subprocess.STDOUT).returncode


def _base_env(app, spec, mode):
    env = {k: v for k, v in os.environ.items()
           if k not in ("DENSE_READY_VALID", "PIPELINED", "MATCH_BRANCH_DELAY", "EXHAUSTIVE_PIPE",
                        "CGRA_DATA_WIDTH", "LAKE_COLLATERAL_JSON_MEM", "LAKE_COLLATERAL_JSON_REGFILE")}
    env.update(GARNET_HOME=str(AHA / "garnet"), TOOL="XCELIUM", LAKE_SPEC_CONFIG=spec, LAKE_SPEC_MODE=mode,
               USE_NON_SPLIT_FIFOS="1",
               PYTHONPATH=":".join(str(AHA / p) for p in ("", "garnet", "MetaMapper", "archipelago", "lassen")))
    params = json.load(open(AHA / "aha/util/application_parameters.json")).get(app, {}).get("default", {})
    env.update({k: str(v) for k, v in params.items()})
    return env


def _built(width, height, dw, fw, mode):
    tag = AHA / "garnet" / ".e2e_built_tag"
    want = f"{width} {height} {dw} {fw} {mode}"
    return tag, want, tag.exists() and tag.read_text() == want and (AHA / "garnet" / "garnet.v").exists()


@pytest.mark.parametrize("app,dw,mode,fw,width,height,guards", CASES,
                         ids=[f"{c[0].split('/')[1]}-dw{c[1]}-{c[2]}-fw{c[3]}" for c in CASES])
def test_app_bit_accurate(tmp_path, app, dw, mode, fw, width, height, guards):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(dict(data_width=dw, in_ports=2, out_ports=2, storage_capacity=8192,
                                    vec_width=fw)))
    flags = (f"--use_sim_sram --glb_tile_mem_size 128 --lake-spec-config {spec} --lake-spec-mode {mode} "
             "--use-non-split-fifos")
    env = _base_env(app, str(spec), mode)
    app_dir = AHA / "Halide-to-Hardware/apps/hardware_benchmarks" / app

    # Fabric (reused while the configuration is the same)
    tag, want, ok = _built(width, height, dw, fw, mode)
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
    if mode == "rv":
        run_env.update(DENSE_READY_VALID="1", EXHAUSTIVE_PIPE="1")
    assert _bash(f"cd {AHA} && aha --dir {AHA} pnr {app} --width {width} --height {height} {flags}",
                 run_env, tmp_path / "pnr.log") == 0, (tmp_path / "pnr.log").read_text()[-3000:]
    rc = _bash(f"cd {AHA} && timeout 3600 aha --dir {AHA} test {app}", run_env, tmp_path / "test.log")
    log = (tmp_path / "test.log").read_text()
    assert rc == 0 and "comparison passed" in log, f"{guards}\n" + log[-3000:]

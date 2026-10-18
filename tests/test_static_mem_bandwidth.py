"""Static compiles refuse a fetch-width-1 MEM whose ports need more SRAM accesses per cycle
than the memory has (clockwork/static-mem-bandwidth-unchecked, 2026-10-18).

Without ready-valid nothing serializes SRAM accesses: on a fw1 single-port memory (one
access per cycle) lake's static port mux keeps the write and silently drops the other
access, so static conv_3_3 (each row bank written and read every cycle) ran to completion
with about half its outputs wrong. clockwork now stops such a compile with "ERROR: static
compile: ports ... access its SRAM in the same cycle". Dual-port fw1 memories (one write and
one read per cycle), wide-fetch memories (their own sram2tb collision search) and
ready-valid compiles (lake's arbiter serializes) are unchanged.

Opt-in (a few minutes per case): AHA_STATIC_MEM_BW=1. Each case copies the app's sources
to a scratch app directory under Halide-to-Hardware/apps/hardware_benchmarks (removed
afterwards) and runs `aha map` (Halide, MetaMapper, clockwork; no CGRA PnR) with a lake
spec. Static pond matmul_rvtry3 on a fw1 single-port spec is refused too, but only at
`aha pnr`: its reschedule after pipelining (PE kernel latency 3) puts the input's last write
and first read in one cycle; `aha map`'s schedule (latency 0) has no clash, so it is not a
case here (clockwork/CLAUDE.md "Static fw1 SRAM port check"). To test a private clockwork build, set AHA_STATIC_MEM_BW_DIR to an aha
tree whose clockwork/ is that build (e.g. symlinks to this tree, clockwork/ -> the private
dir): `aha map` and the app Makefile take clockwork and its lib/ from that tree.
"""
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

AHA = Path(os.environ.get("AHA_STATIC_MEM_BW_DIR", Path(__file__).resolve().parent.parent))
BENCH = AHA / "Halide-to-Hardware/apps/hardware_benchmarks"
pytestmark = pytest.mark.skipif(os.environ.get("AHA_STATIC_MEM_BW") != "1",
                                reason="opt-in: AHA_STATIC_MEM_BW=1 (Halide + clockwork compiles)")

FW1_SP = dict(data_width=16, in_ports=1, out_ports=1, storage_capacity=4096, vec_width=1)
FW1_DP = dict(FW1_SP, dual_port=True)
FW2_SP = dict(data_width=16, in_ports=2, out_ports=2, storage_capacity=8192, vec_width=2)

# app, spec, runtime mode, compiles?, what it guards, extra env (a dict value = a spec file)
CASES = [
    ("tests/conv_3_3", FW1_SP, "static", False, "line buffer: each row bank written and read every cycle", {}),
    ("tests/conv_3_3", FW1_SP, "rv", True, "ready-valid: lake's arbiter serializes the accesses", {}),
    ("tests/conv_3_3", FW1_DP, "static", True, "dual-port: one write and one read per cycle", {}),
    ("tests/conv_3_3", FW2_SP, "static", True, "wide fetch: agg/tb and the sram2tb collision search", {}),
]

SHELL_SETUP = "set +u; source /aha/bin/activate; "


def _env(app, spec, mode, extra, tmp_path):
    env = {k: v for k, v in os.environ.items()
           if k not in ("DENSE_READY_VALID", "PIPELINED", "MATCH_BRANCH_DELAY", "EXHAUSTIVE_PIPE",
                        "LAKE_COLLATERAL_JSON_MEM", "LAKE_COLLATERAL_JSON_REGFILE",
                        "LAKE_POND_SPEC_CONFIG", "MEM_NO_BANDWIDTH_CHECK")}
    env.update(GARNET_HOME=str(AHA / "garnet"), LAKE_SPEC_CONFIG=spec, LAKE_SPEC_MODE=mode)
    if mode == "rv":
        env.update(DENSE_READY_VALID="1", PIPELINED="0", MATCH_BRANCH_DELAY="0")
    params = json.load(open(AHA / "aha/util/application_parameters.json")).get(app, {}).get("default", {})
    env.update({k: str(v) for k, v in params.items()})
    for k, v in extra.items():
        if isinstance(v, dict):
            (tmp_path / f"{k}.json").write_text(json.dumps(v))
            v = tmp_path / f"{k}.json"
        env[k] = str(v)
    return env


@pytest.fixture
def scratch_app(request):
    """A copy of the app's sources two levels under hardware_benchmarks (its Makefile includes
    ../../hw_support), removed afterwards."""
    made = []

    def make(app):
        src = BENCH / app
        if not (src / "Makefile").exists():
            pytest.skip(f"{app} is not in this Halide-to-Hardware tree")
        dst = BENCH / f"_static_bw_{uuid.uuid4().hex[:8]}" / src.name
        shutil.copytree(src, dst, symlinks=True,
                        ignore=shutil.ignore_patterns("bin", "log", "map_result", ".ast_tools", "*.o"))
        made.append(dst.parent)
        return dst.relative_to(BENCH)

    yield make
    for d in made:
        shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("app,spec,mode,compiles,guards,extra", CASES,
                         ids=[f"{c[0].split('/')[1]}-fw{c[1]['vec_width']}"
                              f"{'dp' if c[1].get('dual_port') else 'sp'}-{c[2]}" for c in CASES])
def test_static_fw1_bandwidth(tmp_path, scratch_app, app, spec, mode, compiles, guards, extra):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))
    copy = scratch_app(app)
    log = tmp_path / "map.log"
    with open(log, "w") as f:
        rc = subprocess.run(["bash", "-c", SHELL_SETUP + f"cd {AHA} && aha --dir {AHA} map {copy}"],
                            env=_env(app, str(spec_path), mode, extra, tmp_path), stdout=f,
                            stderr=subprocess.STDOUT).returncode
    text = log.read_text(errors="replace")
    refused = "ERROR: static compile: ports" in text
    if compiles:
        assert rc == 0 and not refused, f"{guards}\n" + text[-3000:]
        if mode == "static" and spec["vec_width"] == 1:  # the check ran on every fw1 bank
            mem_cout = (BENCH / copy / "bin/mem_cout").read_text(errors="replace")
            assert "SRAM ports of" in mem_cout, guards
    else:
        assert rc != 0 and refused and "single-port: one access per cycle" in text, \
            f"{guards}\n" + text[-3000:]

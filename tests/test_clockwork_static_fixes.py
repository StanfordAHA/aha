"""clockwork compile fixes for three gaps in the thesis app matrix (2026-10-28, OPEN_ISSUES
clockwork/static-fw1-dp-stencil, clockwork/static-fw2-dp-resnet, clockwork/resnet-one-input-mem).

- fw1 dual-port, static: the dual-port compile path built its buffers without the PE pipeline
  slack of each compute input (`build_buffers` without the schedule info), so the stencil taps
  of a pipelined PE tree arrived up to 3 cycles apart (gaussian 8398 of 12152 outputs wrong).
  Checked here by the slack lines that only the slack-aware `build_buffers` prints.
- fw2 wide fetch, static: resnet's input TB fetched 14 words per row in its r.x = 1 pass while
  the last column needs word 14 (only the r.x = 2 pass fetched it), so x = 27 read a stale word
  (84 of 2352 outputs low). clockwork now pads the fetch loop when reads have no fetch of
  their word.
- A MEM bank with more data ports than the memory (resnet's MEM accumulator has an init and
  an update writer; the 1-input specs have one) now stops the compile with a message instead
  of a KeyError in garnet's pin remap at PnR.

Opt-in (a few minutes per case): AHA_CLOCKWORK_FIXES=1. Each case copies the app's sources to
a scratch app directory under Halide-to-Hardware/apps/hardware_benchmarks (removed afterwards)
and runs `aha map` (Halide, MetaMapper, clockwork; no CGRA PnR) with a lake spec. The RTL
checks (bit-accurate gaussian/unsharp/harris/camera on fw1 dual-port, resnet on fw2
dual-port) need PnR and a simulator; see clockwork/CLAUDE.md "Thesis matrix compile fixes".
To test a private clockwork build, set AHA_CLOCKWORK_FIXES_DIR to an aha tree whose
clockwork/ is that build.
"""
import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

AHA = Path(os.environ.get("AHA_CLOCKWORK_FIXES_DIR", Path(__file__).resolve().parent.parent))
BENCH = AHA / "Halide-to-Hardware/apps/hardware_benchmarks"
pytestmark = pytest.mark.skipif(os.environ.get("AHA_CLOCKWORK_FIXES") != "1",
                                reason="opt-in: AHA_CLOCKWORK_FIXES=1 (Halide + clockwork compiles)")

FW1_DP = dict(data_width=16, in_ports=1, out_ports=1, storage_capacity=4096, vec_width=1,
              dual_port=True)
FW2_DP = dict(data_width=16, in_ports=2, out_ports=2, storage_capacity=4096, vec_width=2,
              vec_capacity=2, dual_port=True)
FW2_IN1 = dict(data_width=16, in_ports=1, out_ports=1, storage_capacity=2048, vec_width=2,
               vec_capacity=2)

# id, app, spec, runtime mode, expected outcome
CASES = [
    ("gaussian-fw1dp-static", "apps/gaussian", FW1_DP, "static", "slack"),
    ("resnet-fw2dp-static", "apps/resnet", FW2_DP, "static", "pad"),
    ("resnet-fw2in1-static", "apps/resnet", FW2_IN1, "static", "refused"),
    ("resnet-fw2in1-rv", "apps/resnet", FW2_IN1, "rv", "refused"),
]

SHELL_SETUP = "set +u; source /aha/bin/activate; "


def _env(app, spec, mode):
    env = {k: v for k, v in os.environ.items()
           if k not in ("DENSE_READY_VALID", "PIPELINED", "MATCH_BRANCH_DELAY", "EXHAUSTIVE_PIPE",
                        "LAKE_COLLATERAL_JSON_MEM", "LAKE_COLLATERAL_JSON_REGFILE",
                        "LAKE_POND_SPEC_CONFIG", "TB_NO_FETCH_PAD", "TB_NO_REFETCH")}
    env.update(GARNET_HOME=str(AHA / "garnet"), LAKE_SPEC_CONFIG=spec, LAKE_SPEC_MODE=mode)
    if mode == "rv":
        env.update(DENSE_READY_VALID="1", PIPELINED="0", MATCH_BRANCH_DELAY="0")
    params = json.load(open(AHA / "aha/util/application_parameters.json")).get(app, {}).get("default", {})
    env.update({k: str(v) for k, v in params.items()})
    return env


@pytest.fixture
def scratch_app():
    """A copy of the app's sources two levels under hardware_benchmarks (its Makefile includes
    ../../hw_support), removed afterwards."""
    made = []

    def make(app):
        src = BENCH / app
        if not (src / "Makefile").exists():
            pytest.skip(f"{app} is not in this Halide-to-Hardware tree")
        dst = BENCH / f"_cw_fixes_{uuid.uuid4().hex[:8]}" / src.name
        shutil.copytree(src, dst, symlinks=True,
                        ignore=shutil.ignore_patterns("bin", "log", "map_result", ".ast_tools", "*.o"))
        made.append(dst.parent)
        return dst.relative_to(BENCH)

    yield make
    for d in made:
        shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("app,spec,mode,expect", [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_clockwork_static_fixes(tmp_path, scratch_app, app, spec, mode, expect):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))
    copy = scratch_app(app)
    log = tmp_path / "map.log"
    with open(log, "w") as f:
        rc = subprocess.run(["bash", "-c", SHELL_SETUP + f"cd {AHA} && aha --dir {AHA} map {copy}"],
                            env=_env(app, str(spec_path), mode), stdout=f,
                            stderr=subprocess.STDOUT).returncode
    text = log.read_text(errors="replace")
    mem_cout_path = BENCH / copy / "bin/mem_cout"
    mem_cout = mem_cout_path.read_text(errors="replace") if mem_cout_path.exists() else ""
    if expect == "refused":
        assert rc != 0 and "ERROR: compile: memory bank" in text and "1 input" in text, text[-3000:]
        return
    assert rc == 0, text[-3000:]
    if expect == "slack":
        # the slack-aware build_buffers prints one "Slack: N" per compute read port; a pipelined
        # PE tree gives some taps a nonzero slack
        assert re.search(r"^Slack: [1-9]", mem_cout, re.M), "dual-port path built buffers without slack"
    elif expect == "pad":
        assert "padded fetch loop leaves 0 (using it)" in mem_cout, \
            "resnet's input TB fetch loop was not padded"

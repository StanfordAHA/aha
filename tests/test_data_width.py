"""The CGRA data width has one source: the lake spec's data_width.

`aha map` hands the compiler the spec's lake collateral (which carries data_width)
and refuses a collateral, spec or pond collateral of another width; `aha test`
reads the width garnet built (its generated GLB header). 16 without a spec.
"""
import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from aha.util.data_width import collateral_data_width, fabric_data_width, spec_data_width

REPO = Path(__file__).resolve().parent.parent


def _json(path, **fields):
    path.write_text(json.dumps(fields))
    return str(path)


def _spec(tmp_path, width):
    return _json(tmp_path / f"spec_dw{width}.json", data_width=width, in_ports=2, out_ports=2,
                 storage_capacity=8192, vec_width=4)


def test_spec_and_collateral_widths(tmp_path):
    assert spec_data_width(_spec(tmp_path, 32)) == 32
    assert spec_data_width(_json(tmp_path / "s.json", vec_width=4)) == 16
    assert collateral_data_width(_json(tmp_path / "c.json", data_width=64)) == 64
    assert collateral_data_width(_json(tmp_path / "c16.json", capacity=1024)) == 16


def test_fabric_width_from_the_generated_glb_header(tmp_path):
    header = tmp_path / "global_buffer" / "header" / "global_buffer_param.svh"
    assert fabric_data_width(tmp_path) == 16  # no garnet build yet
    header.parent.mkdir(parents=True)
    header.write_text("localparam int CGRA_DATA_WIDTH = 32;\nlocalparam int BANK_DATA_WIDTH = 64;\n")
    assert fabric_data_width(tmp_path) == 32


@pytest.fixture
def app_dir(tmp_path):
    d = tmp_path / "app"
    d.mkdir()
    return d


def _set(args, env, app_dir):
    from aha.util.map import set_lake_collaterals
    set_lake_collaterals(args, env, app_dir)
    return env


def test_collateral_generated_from_the_spec(tmp_path, app_dir):
    # No --collateral: generated from LAKE_SPEC_CONFIG, so it has the fabric's width
    env = _set(Namespace(collateral=None), {"LAKE_SPEC_CONFIG": _spec(tmp_path, 32)}, app_dir)
    assert env["LAKE_COLLATERAL_JSON_MEM"] == str(app_dir / "bin" / "lake_collateral_mem.json")
    assert collateral_data_width(env["LAKE_COLLATERAL_JSON_MEM"]) == 32


def test_given_collateral_of_another_width_is_refused(tmp_path, app_dir):
    coll = _json(tmp_path / "coll32.json", data_width=32)
    with pytest.raises(SystemExit, match="data_width 32.*data_width 16"):
        _set(Namespace(collateral=coll), {"LAKE_SPEC_CONFIG": _spec(tmp_path, 16)}, app_dir)


def test_given_collateral_of_the_same_width(tmp_path, app_dir):
    coll = _json(tmp_path / "coll64.json", data_width=64)
    env = _set(Namespace(collateral=coll), {"LAKE_SPEC_CONFIG": _spec(tmp_path, 64)}, app_dir)
    assert env["LAKE_COLLATERAL_JSON_MEM"] == str(Path(coll).resolve())


def test_pond_collateral_of_another_width_is_refused(tmp_path, app_dir):
    coll = _json(tmp_path / "coll32.json", data_width=32)
    pond = _json(tmp_path / "pond16.json", data_width=16)
    with pytest.raises(SystemExit, match="pond collateral"):
        _set(Namespace(collateral=coll, pond_collateral=pond), {}, app_dir)


def test_no_spec_means_16(app_dir):
    env = _set(Namespace(collateral=None), {}, app_dir)
    assert collateral_data_width(env["LAKE_COLLATERAL_JSON_MEM"]) == 16


def test_cli_registers_only_real_subcommands():
    # aha.py turns every aha/util module into a subcommand; a helper module without
    # add_subparser (as data_width.py was, briefly) breaks every `aha` command.
    out = subprocess.run([sys.executable, "-c", "import sys; sys.argv = ['aha', '--help']; "
                          "from aha.aha import main; main()"],
                         cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-2000:]
    assert "map" in out.stdout and "data_width" not in out.stdout

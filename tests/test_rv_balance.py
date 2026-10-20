"""`aha pnr --rv-balance N` (aha/util/rv_balance.py): when it is on by default, the
environment it refuses, the restore of an earlier run's padded netlist, and one balancing
round on a toy routed design with garnet's model and padding hook (PnR stubbed)."""
import json
from pathlib import Path

import pytest

from aha.util import rv_balance

REPO = Path(__file__).resolve().parent.parent
GARNET = REPO / "garnet"


def test_check_env():
    rv_balance.check_env({"DENSE_READY_VALID": "1", "EXHAUSTIVE_PIPE": "0"}, [])
    for env, extra in (({}, []),
                       ({"DENSE_READY_VALID": "1", "EXHAUSTIVE_PIPE": "1"}, []),
                       ({"DENSE_READY_VALID": "1", "POST_PNR_ITR": "max"}, []),
                       ({"DENSE_READY_VALID": "1"}, ["--daemon", "launch"])):
        with pytest.raises(SystemExit):
            rv_balance.check_env(env, extra)


def test_rounds_default():
    """On by default for dense RV without PnR pipelining or --daemon; an explicit N is
    checked; 0 turns it off."""
    drv = {"DENSE_READY_VALID": "1"}
    assert rv_balance.rounds(None, drv, []) == rv_balance.DEFAULT_ROUNDS
    assert rv_balance.rounds(None, dict(drv, EXHAUSTIVE_PIPE="0"), []) == rv_balance.DEFAULT_ROUNDS
    for env, extra in (({}, []),                                  # static
                       (dict(drv, EXHAUSTIVE_PIPE="1"), []),      # aha regress RV
                       (dict(drv, POST_PNR_ITR="max"), []),
                       (drv, ["--daemon", "use"])):
        assert rv_balance.rounds(None, env, extra) == 0
    assert rv_balance.rounds(0, drv, []) == 0
    assert rv_balance.rounds(2, drv, []) == 2
    with pytest.raises(SystemExit):
        rv_balance.rounds(2, dict(drv, EXHAUSTIVE_PIPE="1"), [])


def _top(instances, connections, metadata=None):
    mod = {"instances": instances, "connections": connections}
    if metadata:
        mod["metadata"] = metadata
    return {"top": "global.app", "namespaces": {"global": {"modules": {"app": mod}}}}


def test_restore(tmp_path):
    b = tmp_path / "bin"
    b.mkdir()
    (b / "design_top.json").write_text(json.dumps(_top({}, [], {"rv_balance": {"registers": 2}})))
    (b / "design_top.pre_rv_balance.json").write_text(json.dumps(_top({"x": {}}, [])))
    for p in (tmp_path / "manual.place", b / "manual.place"):
        p.write_text("p0 1 1\n")
    for f in ("rv_balance_plan.json", "rv_balance_log.json"):
        (b / f).write_text("{}")
    assert rv_balance.balanced(tmp_path)
    rv_balance.restore(tmp_path)
    assert json.loads((b / "design_top.json").read_text()) == _top({"x": {}}, [])
    assert not (tmp_path / "manual.place").exists() and not (b / "manual.place").exists()
    assert not rv_balance.balanced(tmp_path) and not (b / "rv_balance_plan.json").exists()
    # a PnR that does not balance keeps a user's manual.place
    (tmp_path / "manual.place").write_text("p0 1 1\n")
    rv_balance.restore(tmp_path, unpin=False)
    assert (tmp_path / "manual.place").exists()
    # an unpadded netlist (a new map) is left alone
    (b / "design_top.json").write_text(json.dumps(_top({"y": {}}, [])))
    rv_balance.restore(tmp_path)
    assert json.loads((b / "design_top.json").read_text()) == _top({"y": {}}, [])


def _route(path, bit0_regs):
    """No PnR pipelining: IO -> pa; pa res -> pb -> mac data0; pa res_p -> mac bit0
    (through bit0_regs registers); mac res -> output IO."""
    regs = [f"REG T0_NORTH (0, 3, {4 + i}, 1)" for i in range(bit0_regs)]
    nets = [("e1", ["PORT io2f_16 (0, 0, 16)"], "PORT PE_input_width_16_num_0 (3, 3, 16)"),
            ("e2", ["PORT PE_output_width_16_num_0 (3, 3, 16)"], "PORT PE_input_width_16_num_0 (4, 4, 16)"),
            ("e3", ["PORT PE_output_width_16_num_0 (4, 4, 16)"], "PORT PE_input_width_16_num_0 (5, 5, 16)"),
            ("e4", ["PORT PE_output_width_1_num_0 (3, 3, 1)", *regs], "PORT PE_input_width_1_num_0 (5, 5, 1)"),
            ("e5", ["PORT PE_output_width_16_num_0 (5, 5, 16)"], "PORT f2io_16 (1, 0, 16)")]
    lines = []
    for k, (net, head, tail) in enumerate(nets):
        lines += [f"Net ID: {net} Segment Size: 1", "Segment: 0 Size: 9"] + head
        lines += [f"SB ({k}, 1, 1, 0, 1, 16)", tail, ""]
    path.write_text("\n".join(lines) + "\n")


def test_balance_round(tmp_path):
    if not (GARNET / "mflowgen/common/application/rv_throughput.py").exists():
        pytest.skip("needs the sibling garnet checkout")
    b = tmp_path / "bin"
    b.mkdir()
    pe = {"genref": "global.PE"}
    (b / "design_top.json").write_text(json.dumps(_top(
        {"in": {"genref": "global.IO"}, "out": {"genref": "global.IO"},
         "pa": dict(pe), "pb": dict(pe), "mac": dict(pe)},
        [["in.out", "pa.data0"], ["pa.O0", "pb.data0"], ["pb.O0", "mac.data0"],
         ["pa.O1", "mac.bit0"], ["mac.O0", "out.in"]])))
    _route(b / "design.route", 0)
    (b / "design.place").write_text("Block Name X Y #Block ID\n---\n"
                                    "pa 3 3 #p0\npb 4 4 #p1\nmac 5 5 #p2\nin 0 0 #I0\nout 1 0 #I1\n")
    calls = []

    def pnr(env):
        # the pinned re-PnR sees the padded netlist and every block pinned
        calls.append((env["MANUAL_PATH_BALANCE_PLACER"], env["CYCLONE_REG_SEARCH"]))
        top = json.loads((b / "design_top.json").read_text())["namespaces"]["global"]["modules"]["app"]
        regs = [i for n, i in top["instances"].items() if n.startswith("rv_balance_")]
        assert len(regs) == 2 and all(r["modref"] == "corebit.reg" for r in regs)
        assert sorted((tmp_path / "manual.place").read_text().split("\n")) == sorted(
            ["I0 0 0", "I1 1 0", "p0 3 3", "p1 4 4", "p2 5 5", ""])
        _route(b / "design.route", 2)   # the router put the two registers on the bit0 route

    log = rv_balance.balance(tmp_path, GARNET, 3, pnr, {"DENSE_READY_VALID": "1"})
    assert calls == [("1", "1")]
    assert [(r["round"], r["early_inputs"], r["early_stages"], r["padding_registers"]) for r in log] == \
        [(0, 1, 2, 0), (1, 0, 0, 2)]
    assert log[-1]["modelled_rate"] >= 0.995
    assert json.loads((b / "rv_balance_plan.json").read_text()) == {"mac.bit0": 2}
    assert json.loads((b / "rv_balance_log.json").read_text()) == log
    assert not (tmp_path / "manual.place").exists()

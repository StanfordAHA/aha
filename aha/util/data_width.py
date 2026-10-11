"""The CGRA data word width, from the one place it is defined: the lake spec's data_width.

- garnet builds the fabric from the spec (tracks of data_width + 1 bits).
- The spec's lake collateral carries the same data_width to the compiler
  (Halide, clockwork, MetaMapper read it from LAKE_COLLATERAL_JSON_MEM).
- garnet writes it into the generated GLB header the testbench compiles,
  which is what `aha test` and parse_design_meta read.
Without a spec, everything is 16.
"""
import json
import os
import re

DEFAULT_DATA_WIDTH = 16


def spec_data_width(spec_path):
    """data_width of a lake spec config JSON (16 when it has none)."""
    with open(spec_path) as f:
        return int(json.load(f).get("data_width", DEFAULT_DATA_WIDTH))


def collateral_data_width(collateral_path):
    """data_width of a lake collateral JSON (16 when it has none)."""
    with open(collateral_path) as f:
        return int(json.load(f).get("data_width", DEFAULT_DATA_WIDTH))


def fabric_data_width(garnet_dir):
    """CGRA_DATA_WIDTH of the last garnet build (its generated GLB header), 16 if absent."""
    header = os.path.join(str(garnet_dir), "global_buffer", "header", "global_buffer_param.svh")
    if not os.path.exists(header):
        return DEFAULT_DATA_WIDTH
    with open(header) as f:
        m = re.search(r"\bCGRA_DATA_WIDTH\s*=\s*(\d+)", f.read())
    return int(m.group(1)) if m else DEFAULT_DATA_WIDTH

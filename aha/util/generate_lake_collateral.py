"""Generate lake collateral JSON for clockwork compilation.

Builds the same ONYX memory Spec used by garnet (util_onyx.py) and
serializes the compiler collateral to a JSON file that clockwork can
load via the LAKE_COLLATERAL_JSON_<LEVEL> environment variable.
"""

import argparse
import os

from lake.spec.spec_memory_controller import build_four_port_wide_fetch_rv

# Default parameters matching garnet/cgra/util_onyx.py
DEFAULT_STORAGE_CAPACITY = 4096
DEFAULT_DATA_WIDTH = 16
DEFAULT_VEC_WIDTH = 4


def generate_collateral(output_path,
                        storage_capacity=DEFAULT_STORAGE_CAPACITY,
                        data_width=DEFAULT_DATA_WIDTH,
                        vec_width=DEFAULT_VEC_WIDTH):
    """Build the ONYX memory spec and write collateral JSON.

    Args:
        output_path: File path for the output JSON.
        storage_capacity: SRAM capacity in bytes.
        data_width: External data width in bits.
        vec_width: Vector / fetch width.

    Returns:
        The collateral dict that was written.
    """
    spec = build_four_port_wide_fetch_rv(
        storage_capacity=storage_capacity,
        data_width=data_width,
        vec_width=vec_width,
    )
    spec.save_compiler_information(output_path)
    return spec.extract_compiler_information()


def main():
    parser = argparse.ArgumentParser(
        description="Generate lake collateral JSON for clockwork")
    parser.add_argument("output", help="Output JSON file path")
    parser.add_argument("--storage-capacity", type=int,
                        default=DEFAULT_STORAGE_CAPACITY)
    parser.add_argument("--data-width", type=int,
                        default=DEFAULT_DATA_WIDTH)
    parser.add_argument("--vec-width", type=int,
                        default=DEFAULT_VEC_WIDTH)
    args = parser.parse_args()

    collateral = generate_collateral(
        args.output,
        storage_capacity=args.storage_capacity,
        data_width=args.data_width,
        vec_width=args.vec_width,
    )
    print(f"Wrote lake collateral to {args.output}")
    print(f"  controllers: {collateral['controller_name']}")
    print(f"  capacity: {collateral['capacity']}")
    print(f"  fetch_width: {collateral['fetch_width']}")


if __name__ == "__main__":
    main()

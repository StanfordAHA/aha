import argparse
import logging
import os
from pathlib import Path
import pkgutil
import util


def main():
    parser = argparse.ArgumentParser()

    # Logging
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const=logging.INFO,
        default=logging.WARNING,
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_const",
        const=logging.DEBUG,
        default=logging.WARNING,
    )

    # Working directory info
    parser.add_argument(
        "--dir",
        dest="aha_dir",
        type=Path,
        default=Path(os.path.dirname(os.path.abspath(__file__))),
    )

    # Subcommands
    subparser = parser.add_subparsers()

    # Automatically create a command named after each submodule in our
    # `util` module
    for importer, modname, ispkg in pkgutil.iter_modules(util.__path__):
        getattr(util, modname).add_subparser(subparser)

    args, extra_args = parser.parse_known_args()

    logging.basicConfig(level=min(args.verbose, args.debug))

    # Each subcommand sets args.dispatch to the command it wants to
    # execute, accepting `args` as the only argument
    if getattr(args, "dispatch", None):
        args.dispatch(args, extra_args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

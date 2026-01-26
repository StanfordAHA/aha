import argparse
import logging
import os
from pathlib import Path
import pkgutil
import aha.util
import subprocess


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
        default=Path(os.path.dirname(os.path.abspath(__file__))).parent,
    )

    # Subcommands
    subparser = parser.add_subparsers()

    # Automatically create a command named after each submodule in our
    # `aha.util` module
    for importer, modname, ispkg in pkgutil.iter_modules(aha.util.__path__):
        if modname == 'regress_util': continue  # Skip helper modules!
        getattr(aha.util, modname).add_subparser(subparser)

    args, extra_args = parser.parse_known_args()

    logging.basicConfig(level=min(args.verbose, args.debug))

    # Each subcommand sets args.dispatch to the command it wants to
    # execute, accepting `args` as the only argument
    if getattr(args, "dispatch", None):

        # Keeping this as a catchall backup; the SIGSEGV should have already
        # been caught by similar retry mechanisms in garnet.py and regress.py
        for retry in [1, 2, 3]:  # In case of SIGSEGV, retry up to three times
            try:
                args.dispatch(args, extra_args)
                break
            except subprocess.CalledProcessError as e:
                if 'SIGSEGV' in str(e):
                    print(f'\n\n{e}\n')  # Print the error msg
                    print(f'*** ERROR subprocess died {retry} time(s) with SIGSEGV')
                    print('*** Will retry three times, then give up.\n\n')
                    if retry == 3:
                        raise
                else:
                    raise

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

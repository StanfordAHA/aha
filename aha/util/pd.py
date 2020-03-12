import os
from pathlib import Path
from aha.util.docker import in_docker


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem)
    pd_subparser = parser.add_subparsers(dest="pd_command")
    pd_init_parser = pd_subparser.add_parser("init")
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    if args.pd_command == "init":
        if in_docker():
            os.symlink("/tsmc16-adk", f"{os.environ['MFLOWGEN']}/adks/tsmc16")
        else:
            raise NotImplementedError

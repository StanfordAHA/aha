import json
from pathlib import Path


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    with open(args.aha_dir / "config.json", "w") as f:
        config = {
            "width": args.width,
            "height": args.height,
        }
        json.dump(config, f)

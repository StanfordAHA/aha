import argparse
import logging
import subprocess
import sys
import os
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    # Logging
    parser.add_argument('-v', '--verbose',
                        action="store_const", const=logging.INFO, default=logging.WARNING)
    parser.add_argument('-d', '--debug',
                        action="store_const", const=logging.DEBUG, default=logging.WARNING)

    subparser = parser.add_subparsers(dest='command')

    garnet_parser = subparser.add_parser('garnet', add_help=False)
    # garnet_parser.add_argument('args', nargs=argparse.REMAINDER)


    args, extra_args = parser.parse_known_args()
    print(args)

    logging.basicConfig(level=min(args.verbose, args.debug))

    if args.command == 'garnet':
        subprocess.call(
            [sys.executable, 'garnet.py'] + extra_args,
            cwd=Path(os.path.dirname(os.path.abspath(__file__))) / 'garnet',
        )


if __name__ == '__main__':
    main()


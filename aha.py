import argparse
import copy
import docker
import git
import json
import logging
import subprocess
import sys
import os
from pathlib import Path


AHA_DIR = Path(os.path.dirname(os.path.abspath(__file__)))


def in_docker():
    return os.path.exists('/.dockerenv')


def test():
    aha_dir = os.path.dirname(os.path.abspath(__file__))
    aha_repo = git.Repo(aha_dir)
    aha_branch = aha_repo.head.ref

    docker_tag = 'latest' if aha_branch == aha_repo.heads.master else str(aha_branch)

    client = docker.from_env()

    try:
        image = client.images.get(f'stanfordaha/garnet:{docker_tag}')
    except docker.errors.ImageNotFound:
        logging.warning(f"Pulling 'stanfordaha/garnet:{docker_tag}' from registry...")
        image = client.images.pull('stanfordaha/garnet', tag=docker_tag)

    logging.info("Checking registry for updates...")
    latest_data = client.images.get_registry_data('stanfordaha/garnet')

    if image.id != latest_data.id:
        logging.warning(f"An update for 'stanfordaha/garnet:{docker_tag}' is available.")
        logging.warning(f"Run `docker pull stanfordaha/garnet:{docker_tag}` to update.")

    # print(client.containers.run(image, "echo hello world"))


def main():
    parser = argparse.ArgumentParser()
    # Logging
    parser.add_argument('-v', '--verbose',
                        action="store_const", const=logging.INFO, default=logging.WARNING)
    parser.add_argument('-d', '--debug',
                        action="store_const", const=logging.DEBUG, default=logging.WARNING)

    subparser = parser.add_subparsers(dest='command')

    halide_parser = subparser.add_parser('halide', add_help=False)
    halide_parser.add_argument('app')

    map_parser = subparser.add_parser('map', add_help=False)
    map_parser.add_argument('app')

    garnet_parser = subparser.add_parser('garnet', add_help=False)
    # garnet_parser.add_argument('args', nargs=argparse.REMAINDER)

    test_parser = subparser.add_parser('test', add_help=False)
    test_parser.add_argument('app')

    config_parser = subparser.add_parser('config', add_help=False)
    test_parser.add_argument('--width', type=int)
    test_parser.add_argument('--height', type=int)

    args, extra_args = parser.parse_known_args()

    logging.basicConfig(level=min(args.verbose, args.debug))

    if not in_docker():
        test()

    if args.command == 'config':
        with open(AHA_DIR/'config.json', 'w') as f:
            config = {
                'width': args.width,
                'height': args.height,
            }
            json.dump(config, f)
    elif args.command == 'halide':
        args.app = Path(args.app)
        env = copy.deepcopy(os.environ)
        env['COREIR_DIR'] = str(AHA_DIR/'coreir-apps')
        halide_dir = AHA_DIR/'halide-to-hardware'
        app_dir = halide_dir/Path('apps/hardware_benchmarks')/args.app

        # CoreIR Output
        subprocess.call(
            ['make', '-C', app_dir, 'design-coreir'],
            cwd=AHA_DIR/'halide-to-hardware',
            env=env,
        )

        subprocess.call(
            [sys.executable, 'coreir_gen.py', app_dir/'bin/design_top.json'],
            cwd=AHA_DIR/'BufferMapping/script/',
            env=env,
        )

        os.rename(
            AHA_DIR/'BufferMapping/script/output/design_top_rewrite.json',
            app_dir/'bin/design_top.json',
        )

        # Raw Images
        subprocess.call(
            ['make', '-C', app_dir, 'bin/input.raw', 'bin/output_cpu.raw'],
            cwd=AHA_DIR/'halide-to-hardware',
            env=env,
        )

        os.rename(
            app_dir/'bin/output_cpu.raw',
            app_dir/'bin/gold.raw',
        )
    elif args.command == 'garnet':
        subprocess.call(
            [sys.executable, 'garnet.py'] + extra_args,
            cwd=AHA_DIR/'garnet',
        )
    elif args.command == 'map':
        args.app = Path(args.app)
        app_dir = Path(f'{AHA_DIR}/halide-to-hardware/apps/hardware_benchmarks/{args.app}')

        map_args = [
            '--no-pd',
	    '--interconnect-only',
            '--input-app', app_dir/'bin/design_top.json',
            '--input-file', app_dir/'bin/input.raw',
            '--output-file', app_dir/f'bin/{args.app.name}.bs',
            '--gold-file', app_dir/'bin/gold.raw',
        ]

        subprocess.call(
            [sys.executable, 'garnet.py'] + map_args + extra_args,
            cwd=AHA_DIR/'garnet',
        )
    elif args.command == 'test':
        args.app = Path(args.app)
        app_dir = Path(f'{AHA_DIR}/halide-to-hardware/apps/hardware_benchmarks/{args.app}')

        subprocess.call(
            [sys.executable, 'tbg.py', 'garnet.v', 'garnet_stub.v', app_dir/f'bin/{args.app.name}.bs.json'],
            cwd=AHA_DIR/'garnet',
        )


if __name__ == '__main__':
    main()

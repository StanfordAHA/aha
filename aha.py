import argparse
import docker
import git
import logging
import subprocess
import sys
import os
from pathlib import Path


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

    print(client.containers.run(image, "echo hello world"))


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

    logging.basicConfig(level=min(args.verbose, args.debug))

    if not in_docker():
        test()

    if args.command == 'garnet':
        subprocess.call(
            [sys.executable, 'garnet.py'] + extra_args,
            cwd=Path(os.path.dirname(os.path.abspath(__file__))) / 'garnet',
        )


if __name__ == '__main__':
    main()


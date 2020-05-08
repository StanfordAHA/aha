import docker
import getpass
import logging
import os
from pathlib import Path


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem)
    parser.add_argument("--tag", default="latest")
    parser.add_argument("--tsmc-adk", default=None)
    parser.add_argument("--mc", default=None)
    parser.add_argument("-p", "--persistent", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("-n", "--name", default=None, type=str)
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    volumes = {}
    if os.path.exists("/cad"):
        volumes["/cad"] = {
            "bind": "/cad",
            "mode": "ro",
        }

    if os.path.exists("/tsmc16"):
        volumes["/tsmc16"] = {
            "bind": "/tsmc16",
            "mode": "ro",
        }

    if args.tsmc_adk:
        # TODO: this should really be ro not rw but mflowgen has problems
        volumes[args.tsmc_adk] = {
            "bind": "/tsmc16-adk",
            "mode": "rw",
        }

    if args.mc:
        # TODO: would ideally like to not mount it to /sim/ajcars/mc_clean
        volumes[args.mc] = {
            "bind": "/sim/ajcars/mc_clean",
            "mode": "ro",
        }

    client = docker.from_env()
    # image = client.images.get(f'stanfordaha/garnet:{args.tag}')

    logging.info("Starting container...")
    container = client.containers.run(
        f"stanfordaha/garnet:{args.tag}",
        "bash",
        auto_remove=not args.persistent,
        detach=True,
        name=args.name,
        stdin_open=True,
        tty=True,
        volumes=volumes,
    )

    container_id = f"{getpass.getuser()}-{container.name}"
    container.rename(container_id)

    logging.info("Container started!")

    if not args.persistent:
        logging.warning("The container will be automatically deleted once exited.")
    else:
        logging.warning("This container won't be deleted when you exit. Please clean it up manually when you're done.")

    logging.info(f"Run `docker attach {container_id}` to use it.")
    print(container_id)


def test():
    aha_dir = os.path.dirname(os.path.abspath(__file__ + "/.."))
    aha_repo = git.Repo(aha_dir)
    aha_branch = aha_repo.head.ref

    docker_tag = "latest" if aha_branch == aha_repo.heads.master else str(aha_branch)

    client = docker.from_env()

    try:
        image = client.images.get(f"stanfordaha/garnet:{docker_tag}")
    except docker.errors.ImageNotFound:
        logging.warning(f"Pulling 'stanfordaha/garnet:{docker_tag}' from registry...")
        image = client.images.pull("stanfordaha/garnet", tag=docker_tag)

    logging.info("Checking registry for updates...")
    latest_data = client.images.get_registry_data("stanfordaha/garnet")

    if image.id != latest_data.id:
        logging.warning(
            f"An update for 'stanfordaha/garnet:{docker_tag}' is available."
        )
        logging.warning(f"Run `docker pull stanfordaha/garnet:{docker_tag}` to update.")

    # print(client.containers.run(image, "echo hello world"))


def in_docker():
    return os.path.exists("/.dockerenv")

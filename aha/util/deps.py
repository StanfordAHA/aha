import ast
import networkx as nx
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from pathlib import Path
import pip
import requirements

if Version(pip.__version__) >= Version("20"):
    from pip._internal.network.session import PipSession
else:
    from pip._internal.download import PipSession


def add_subparser(subparser):
    parser = subparser.add_parser(Path(__file__).stem)
    dep_subparser = parser.add_subparsers(dest="dep_command")
    dep_install_parser = dep_subparser.add_parser("install")
    parser.set_defaults(dispatch=dispatch)


def dispatch(args, extra_args=None):
    if args.dep_command == "install":
        import os
        import subprocess
        import sys

        def install(package):
            if os.path.exists(os.path.join(package, "setup.py")):
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-e", package],
                )

        # TODO: only install these if they're not present in `pip list`

        modules = {
            "APEX": "APEX",
            "archipelago": "archipelago",
            "ast_tools": "ast_tools",
            "buffer-mapping": "BufferMapping",
            "canal": "canal",
            "coreir": "pycoreir",
            "cosa": "cosa",
            "fault": "fault",
            "garnet": "garnet",
            "gemstone": "gemstone",
            "hwtypes": "hwtypes",
            "kratos": "kratos",
            "lake": "lake",
            "lassen": "lassen",
            "magma-lang": "magma",
            "mantle": "mantle",
            "peak": "peak",
            "pycyclone": "cgra_pnr/cyclone",
            "pythunder": "cgra_pnr/thunder",
            "mflowgen": "mflowgen",
            "metamapper": "MetaMapper",
            "peak_gen": "peak_generator",
            "Lego_v0": "Lego_v0"
        }

        for dep in order_deps(modules):
            install(os.path.join(args.aha_dir, modules[dep]))

        # TODO: `pip list` and ensure that all the above are pointing to sources


# handle discrepancies between python 3.7/3.8
def parse_install_requires(elts):
    if len(elts) == 0:
        return []

    # python 3.8
    if isinstance(elts[0], ast.Constant):
        return list(map(lambda x: Requirement(x.value), elts))
    # python 3.7
    elif isinstance(elts[0], ast.Str):
        return list(map(lambda x: Requirement(x.s), elts))
    else:
        raise NotImplementedError(f"Couldn't parse install_requires. {elts}")


# looks for the `install_requires` kwarg in an ast.Expr corresponding
# to a call to `setuptools.setup`
def get_install_requires(expr):
    for keyword in expr.value.keywords:
        if keyword.arg == "install_requires":
            return parse_install_requires(keyword.value.elts)
    return []


# looks through the AST to find a call to `setup` and then returns a
# list of parsed requirements
def parse_setup(filename):
    with open(filename) as f:
        for expr in ast.parse(f.read()).body:
            if not isinstance(expr, ast.Expr):
                continue

            if not isinstance(expr.value, ast.Call):
                continue

            if not isinstance(expr.value.func, ast.Name):
                continue

            if not expr.value.func.id == "setup":
                continue

            return get_install_requires(expr)


# gets the requirements from a `setup.py` and/or `requirements.txt` in
# the directory specified by module, and returns them as a dict with a
# version specifier as the values.
def get_reqs(module):
    reqs, reqs_found = [], False
    filename = Path(module)

    if (filename / "setup.py").exists():
        reqs += parse_setup(filename / "setup.py")
        reqs_found = True

    if (filename / "requirements.txt").exists():
        with open(filename / "requirements.txt", "r") as f:
            reqs += requirements.parse(f)
        reqs_found = True

    if not reqs_found:
        raise NotImplementedError(f"Can't get requirements of `{filename}`")

    return {req.name: req.specifier for req in reqs}


def build_dependency_graph(deps):
    G = nx.DiGraph()
    for dep, loc in deps.items():
        cur_reqs = get_reqs(loc)
        G.add_node(dep)
        G.add_edges_from([(req, dep) for req in cur_reqs if req in deps])

    return G


# returns a topologically sorted list of dependencies
def order_deps(deps):
    return nx.topological_sort(build_dependency_graph(deps))


# outputs a dependency graph of the python modules to `./deps.dot`
def draw_deps(deps):
    nx.drawing.nx_pydot.write_dot(build_dependency_graph(deps), "deps.dot")

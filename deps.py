import ast
import networkx as nx
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from pathlib import Path
from pip._internal.req import parse_requirements
from pip._internal.download import PipSession


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
    print(astor.dump_tree(expr))
    for keyword in expr.value.keywords:
        if keyword.arg == 'install_requires':
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

            if not expr.value.func.id == 'setup':
                continue

            return get_install_requires(expr)


# gets the requirements from a `setup.py` and/or `requirements.txt` in
# the directory specified by module, and returns them as a dict with a
# version specifier as the values.
def get_reqs(module):
    reqs, reqs_found = [], False
    filename = Path(module)

    if (filename/'setup.py').exists():
        reqs += parse_setup(filename/'setup.py')
        reqs_found = True

    if (filename/'requirements.txt').exists():
        reqs += parse_requirements(str(filename/'requirements.txt'), session=PipSession())
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
    nx.drawing.nx_pydot.write_dot(build_dependency_graph(deps), 'deps.dot')

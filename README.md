[![Documentation Status](https://readthedocs.org/projects/aha/badge/?version=latest)](https://aha.readthedocs.io/en/latest/?badge=latest)

# How to run locally
You need to have docker installed on your local machine. Please follow
[this guide](https://docs.docker.com/install/) to install Docker CE version.

After installing docker, please follow the commands below
```Bash
# install the aha wrapper script
pip install -e .

# pull docker image from docker hub (this takes a while!)
docker pull stanfordaha/garnet:latest

# run the container in the background and delete it when it exits
# (this will print out the name of the container to attach to)
aha docker

# you can also do the following instead, but using the wrapper shim is
# suggested as it will do things like mount /cad automatically when 
# detected
# docker run -d -it --rm stanfordaha/garnet bash

# attach to the container name printed out above
docker attach <container-name>

# load required simulator (ncsim)
module load incisive

# run a small regression suite
aha regress pr
```


### Simple Demo – Gaussian Blur
<i>Also see slide 3 of [tutorial](https://raw.githubusercontent.com/StanfordAHA/aha_tutorial/main/assets/images/13_EndtoEnd.pdf).</i>
```
# Generate hardware for a 4x16 CGRA
cd /aha/; rm garnet/garnet.v  # Remove previously cached RTL
aha garnet --width 4 --height 16 --verilog --use_sim_sram --glb_tile_mem_size 128

# Choose a verilog simulator for testing
export TOOL=VCS        # To use VCS verilog simulator (default) OR
export TOOL=XCELIUM    # For Cadence Xcelium OR
export TOOL=VERILATOR  # Requires verilator 5.028 or better OR

# Run the test
aha map apps/gaussian
aha pnr apps/gaussian --width 4 --height 16
aha test apps/gaussian
```

### Bigger Demo – Camera Pipeline Using Full 32x16 Array
<i>Also see slide 6 of [tutorial](https://raw.githubusercontent.com/StanfordAHA/aha_tutorial/main/assets/images/13_EndtoEnd.pdf).</i>
```
# Generate hardware for a 32x16 CGRA
cd /aha/; rm garnet/garnet.v  # Remove previously cached RTL
aha garnet --width 32 --height 16 --verilog --use_sim_sram --glb_tile_mem_size 128  # (~20 mins)

# Choose a verilog simulator for testing
export TOOL=VCS        # To use VCS verilog simulator (default) OR
export TOOL=XCELIUM    # For Cadence Xcelium OR
export TOOL=VERILATOR  # Requires verilator 5.028 or better OR

# Run the test
aha map apps/camera_pipeline_2x2
aha pnr apps/camera_pipeline_2x2 --width 32 --height 16
aha test apps/camera_pipeline_2x2
```


# Managing Grouped Dependency Updates

It is inevitable that upstream dependencies change their APIs and
break compatibility. Before we get into how to manage mass upgrades of
dependencies, we'll outline a few steps that, when possible, avoid
this problem.

- Upstream module adds new API features and marks the old ones as
  deprecated.

- Downstream module updates to use the new API.

- Upstream module makes breaking API change and removes compatibility
  with old API.

By doing this, CI builds will always remain successful and you avoid
the problem of having to update multiple dependencies simultaneously,
assuming the downstream modules are brought up-to-date in a timely
manner.

Of course, this isn't always how things end up happening so here's
what to do when needed:

## Manually updating a branch

To manually handle the mass upgrades, we need to do a few
things. First we'll set up a branch for the upgrades. If this is an
upgrade expected to take a long time (e.g. weeks), you might want to
set up Dependabot as explained in the later sections and name the
branch starting with `dev/`.

By setting the branch name as `dev/` we allow the GitHub Actions CI to
automate Dependabot merges into the branch when at least the same
number of checks pass (you might want this behavior because it's
likely that most of the checks will be failing, and as dependencies
update more checks should pass. Without this, you would have to
manually merge in Dependabot pull requests to the branch which gets
tedious very fast).

Once we have the branch set up, the plan is to have it continually
fail CI checks as updates are merged in, and once the CI checks
successfully complete it can be merged back into `master` or whichever
branch was the original target.

# Configuring a branch

Branches represent different sets of dependencies of the full
flow. While the `master` branch is intended to always be the latest
working versions of everything, branches have a few different uses. A
branch that doesn't have automatic updates can be useful for freezing
a set of dependencies entirely, like when you need to get consistent
and repeatable results for a paper. Another use is to track different
branches of modules with many dependencies - CoreIR does this in the
`coreir-dev` branch to see if/how changes on the dev branch break
downstream dependencies. Lastly branches can be used for coordinating
grouped updates, such as when APIs break compatibility in heavily
depended modules.

Each branch is by default set to build a Docker image and publish it
to DockerHub, so one benefit of creating a branch is that others
needing to use the same setup can easily replicate it by cloning the
image.

## Changing the tracked branches of submodules

To set up a new branch to track a different branch of a dependency
(e.g. `coreir` tracking `dev` instead of `master`), create a new
branch of this repo and modify the `.gitmodules` with the modified
branch for the relevant submodules.

```
[submodule "coreir"]
    path = coreir
    url = https://github.com/rdaly525/coreir
    branch = dev
```

## Enabling Dependabot Updates

To enable dependabot to automatically update the submodules in a
branch, the `.dependabot/config.yml` on `master` needs to be
updated. A new entry needs to be added to `update_configs`, and should
probably just be identical to the others with a different
`target_branch`. For example, here is the `update_configs` entry for
`master`:

```
  - package_manager: "submodules"
    target_branch: "master"
    directory: "/"
    update_schedule: "daily"
    automerged_updates:
      - match:
          dependency_type: "all"
          update_type: "all"
```

Once added to the `config.yml`, dependabot should be set up to make
pull requests for your new branch. More information about setting up
the config file can be fould
[here](https://dependabot.com/docs/config-file/). You might want to
set `default_reviewers` or `default_assignees` to yourself for your
branch.

# Configuring a fork

Much like configuring a branch, it's possible to configure a fork. You
might want to use a fork rather than a branch for things like papers
so it doesn't clutter the main repo with additional noise. If you want
the fork to be private rather than public, [here is a guide explaining
how to do
so](https://gist.github.com/0xjac/85097472043b697ab57ba1b1c7530274). Forks
will not publish images to DockerHub unless you set them up to.

## Enabling GitHub Actions CI
TODO: Document

## Enabling Dependabot Updates
TODO: Document

# Docker crash course

Create a new image:
- `docker build .`

List images:
- `docker images`

Start and enter an image:
- `docker run -it <image-id>`

List containers:
- `docker container ls`

Delete stopped containers:
- `docker container prune`

Clean up all unused docker things:
- `docker system prune -a`

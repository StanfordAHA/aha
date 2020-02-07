This file describes the philosophy and structure of this system, so
that others wishing to adapt it to their own uses or extend it further
can understand how things work and why certain choices were made.

- [Background](#background)

# Background

The Stanford Agile Hardware project is focused on creating open-source
tools for designing hardware and validating the usefulness of said
tools by using them as a base to create ASICs on recent technology
nodes. As such, we have a combination of tightly coupled tools that
are used to generate Verilog and other collateral, which is then fed
through proprietary tools for doing technology mapping, layout,
simulation, and analysis of the design.

Each tool we create is owned by a small handful of people and the
groups of people working on each tool are typically disjoint. Despite
this, the tools are interdependent in a way that occasionally means
several tools need to be updated in lockstep, or else the toolchain
breaks.


In our case, there are two major groups in our flow:

- [Front End](#front-end) which is roughly everything that leads up to
  the generation of our Verilog design.

- [Back End](#back-end) which takes a Verilog design as input and runs
  applications on it, synthesizes netlists and other files for
  tapeout, etc.


## Requirements

- Anybody should be able to run anything in the system with minimal
  trouble (provided they have access to the necessary machines).
  Everything that a person new to the group could want to do that
  combines multiple tools (e.g. generate the Verilog output) will have
  a command with sane defaults. We want to eliminate the need to ask
  the one person in the group that knows how to do things and being
  blocked until they get around to replying, or having to dig through
  READMEs in various folders of repos you might not even be aware
  exist.

- All tools should have a single working version installed in the
  flow. The tight coupling of tools means that multiple tools need to
  be updated at the same time. If a downstream tool lags behind, this
  causes problems with conflicting versions. New versions of the tools
  may produce output that breaks on downstream tools using older
  versions. Coordinating mass updates across multiple projects is
  non-trivial. Having each tool pin their own version requirements is
  insufficient since the tools take the output of other tools as
  input. Forcing the master branch of each tool to work in the
  full-flow is bad because external users may want new features, and
  this goes against 'agile' development ideals. At one point we had
  four different version requirements for one of the core libraries in
  our system, which resulted in fragile scripts and lots of hackery
  with `LD_LIBRARY_PATH` that should have been unnecessary.

  - Note that this is per-flow. There might be multiple flows per
    system for reasons below.

- Upgrading dependencies should be straightforward and done
  regularly. While pinning dependencies might be necessary for
  maintaining stability, we want to always be using the latest
  compatible versions of our tools. Updating requirements on a
  per-repo basis would result in version conflicts, so we need to
  specify them separately here.

- The flow needs to be able to freeze all dependencies. When working
  on a paper and trying to do analysis of your results, its annoying
  when you need to figure out if the differences are due to something
  upstream updating how Verilog gets generated or if they are due to
  the changes you're actually trying to measure.

- Running parts of the flow (especially in the back-end) can take
  several hours. In order to remove roadblocks for people that need to
  test things and don't really care about how their inputs were
  generated, these pieces of collateral should be cached frequently on
  machines we use so we can avoid unnecessary recomputation.

- Automated builds/tests occasionally have information that should
  probably be confidential. This repo should serve as a single place
  to manage all scripts related to filtering, so that everybody
  doesn't need to recreate the filters when they want to run new jobs.

- It should be possible to run partial segments of the flow with
  handcrafted inputs. It's not always the case (especially during
  early exploration) that there will be a fully working system that
  generates the inputs you need. To work around this it's common to
  create handcrafted inputs that serve as a target to be matched, but
  downstream parts of the flow still need to run on these inputs
  successfully.

# Structure

## Front End

The front end is primarily a function of the tools used to create the
design, and is handled in this case by using docker images that are
built by CI in this repo. This repo works by creating a docker image
to run integration tests, and once those are successful the image is
published for others in our group to use.

- **TODO** Ideally this setup would also be possible without docker,
    to ease the burden on someone using the tools, since development
    in a docker image is typically not as pleasant as developing on
    the user's environment, and also requires that the user knows how
    to use docker.

Because of this, we use submodules for all the tools in our system.

- **TODO** It's a bit unfortunate that this repo has to serve as a
    'top' repository that contains all the others. Is there another
    way of doing this in a simple way that works? It would be nice to
    just discover the environment that exists on the user's machine
    and use what's there...

- **TODO** How should we manage overriding tools in the front end with
    a version that the user is developing and wants to run the flow to
    test? In this case it needs to probably point to a folder on their
    filesystem instead of the submodule.

## Back End

The back end of the system is largely

## Requirements

### Keeping a Working Set of Dependencies

In order to maintain a working set of dependencies, we pin them to
specific commits of their respecive repos. I don't think there is
another way of doing this while preserving your sanity. Maybe it's not
'agile' but when one typo prevents everyone else in the group from
working I'd rather not be.

### Upgrading Dependencies

Upgrading dependencies manually is not necessary in most
situations. Usually a single repository has a few non-breaking
commits, and if it passes the automated tests it is safe to
upgrade. To automate this, we've set up dependabot on the repository
to make pull requests daily with the updated submodules, and
automatically merge them once the tests pass.

In cases where multiple tools need to be updated simultaneously, we
handle this by creating a development branch with the updated tools,
which fails tests. As more components are updated, more tests begin to
pass, and once all tests are green this branch is merged back into
master. These branches unconditionally update all submodules daily to
their latest versions.

- **TODO** Maybe these should update only if at least the same number
  of tests pass on the branch?

- **TODO** This also needs to update the repositories we depend on and
    notify the maintainers when they have broken something that
    requires manual intervention. Ideally this would be dependabot
    filing an issue in those repositories.

- **TODO** How can we encourage and make it simple for users to update
    their docker images frequently?

### Freezing Dependencies

Freezing dependencies is done with branches/forks. Branches other than
dev/master are configured to not be updated automatically by
dependabot. If someone needs to selectively update some components in
their branch, they can do so by treating their branch as a normal git
repository that uses submodues.

### Caching


# Misc

## Relative Submodule Paths

You can have relative paths (e.g. `../../StanfordAHA/garnet` instead
of `https://github.com/StanfordAHA/garnet`) in `.gitmodules` which
allows someone that clones the repo to automatically clone the
submodules as ssh or http depending on how they cloned the initial
repository. This is super convenient for a user. One problem with this
though is the GitHub website doesn't give you clickable URLs for
submodules specified in this manner.
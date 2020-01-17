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

# Configuring a branch

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
so](https://gist.github.com/0xjac/85097472043b697ab57ba1b1c7530274).

## Enabling GitHub Actions CI
TODO: Document

## Enabling Dependabot Updates
TODO: Document

## Changing the tracked branches of submodules
TODO: Document

#!/bin/bash

# What this script does:
# - Check out aha branch BUILDKITE_COMMIT if build triggered from aha repo.
# - Else check out master if triggered from submod push/pull.
# - Update and initialize all submodules.
# - If triggered from submod, update submod to match commit hash of triggering repo.

# Setup
set +u    # nounset? not on my watch!
set +x    # debug OFF
PS4=">"   # Prevents "+++" prefix during 3-deep "set -x" execution

echo "+++ BEGIN custom-checkout.sh"
echo I am in dir `pwd`

# Checkout master or BUILDKITE_COMMIT

cd $BUILDKITE_BUILD_CHECKOUT_PATH
# REQUEST_TYPE comes from set-trigfrom-and-reqtype.sh
if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then

    # Submod pull request uses aha master branch
    echo "Pull request from a submod repo: check out aha master branch"

    # submod steps do this:
    #   git clone aha
    #   (BUG? should do: git checkout DEV_BRANCH || echo okay)
    #   upload pr_trigger (triggers aha-flow)
    #
    # aha-flow steps do this:
    #   git clone aha
    #   git checkout BUILDKITE_COMMIT || echo okay
    #   git checkout BUILDKITE_COMMIT || git checkout DEV || echo okay
    #   upload pipeline.yml
    #
    # pipeline.yml does this:
    #   BDI pre-checkout:
    #     git clone aha
    #     git checkout DEV_BRANCH
    #     source update-pre-repo.sh: sets BUILDKITE_COMMIT to submod commit hash COMMIE
    #     source set-trigfrom...sh
    #     ~/bin/status-update
    #     source custom_checkout.sh (this file)

    # FIXME aha-submod-flow should set the aha branch;
    # e.g. if aha-submod-flow steps were trying out a dev branch, this would undo that!
    # FIXME add some kind of "assert branch == master" here to verify this clause is unnecessary!

    cur_commit=`git rev-parse HEAD | cut -b 1-7`
    master_commit=`git rev-parse master | cut -b 1-7`
    if [ "cur_commit" != "master_commit" ]; then
        echo "--- WARNING current aha hash $cur_commit != master commit $master_commit"
    fi

    set -x
    git rev-parse HEAD

    # Haha note "fetch" command DOES NOT CHANGE BRANCH
    # i.e. if we were on "branch-foo" before, we are sill on "branch-foo"
    git fetch -v --prune -- origin master
    git checkout -qf standalone-conv2 || git checkout -qf master
    set +x

else
    echo "Push or PR from aha repo: check out requested aha branch $BUILDKITE_COMMIT"
    git fetch -v --prune -- origin $BUILDKITE_COMMIT
    git checkout -qf $BUILDKITE_COMMIT
fi

echo "--- Initialize all submodules YES THIS TAKES AWHILE"

set -x
git submodule update --checkout # This is probably unnecessary but whatevs
git submodule foreach --recursive "git clean -ffxdq"
git submodule sync --recursive
echo "--- git submodule update --init --recursive --force"
git submodule update --init --recursive --force
echo '--- git submodule foreach --recursive "git reset --hard"'
git submodule foreach --recursive "git reset --hard"
set +x

# Update submod

# Note PR_REPO_TAIL comes from set-trigfrom-and-reqtype.sh
if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then
    echo "--- Update submodule '$PR_REPO_TAIL' w commit '$BUILDKITE_COMMIT'"
    (set -x; cd $PR_REPO_TAIL; git fetch origin && git checkout $BUILDKITE_COMMIT)
fi

echo "--- END custom-checkout.sh"

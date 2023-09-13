#!/bin/bash

# What this script does:
# - Clone the aha repo locally.
# - Check out aha branch BUILDKITE_COMMIT if build triggered from aha repo.
# - Else check out master if triggered from submod push/pull.
# - Update and initialize all submodules.
# - If triggered from submod, update submod to match commit hash of triggering repo.

# Setup
set +u    # nounset? not on my watch!
set +x    # debug OFF
PS4="_"   # Prevents "+++" prefix during 3-deep "set -x" execution

echo "+++ custom-checkout.sh BEGIN"
echo I am in dir `pwd`

set -x

# Checkout master or BUILDKITE_COMMIT

if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then
    echo "Pull request from a submod repo: check out aha master branch"
    git fetch -v --prune -- origin master
    git checkout -qf master
else
    echo "Push or PR from aha repo: check out requested aha branch"
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

if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then
    echo "--- Update submodule '$PR_REPO_TAIL' w commit '$BUILDKITE_COMMIT'"
    (set -x; cd $PR_REPO_TAIL; git fetch origin && git checkout $BUILDKITE_COMMIT)
fi

echo "--- custom-checkout.sh END"

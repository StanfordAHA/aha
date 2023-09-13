#!/bin/bash

# What this script does:
# - Update and initialize all aha repo submodules.
# - Check out aha branch BUILDKITE_COMMIT if build triggered from aha repo
#   or AHA DEFAULT (no-heroku now, master later) if triggered from submod push/pull.
# - If triggered from submod, update submod to match commit hash of triggering repo.

# Setup
set +u    # nounset? not on my watch!
set +x    # debug OFF
PS4="_"   # Prevents "+++" prefix during 3-deep "set -x" execution

echo "--- CHECKOUT FULL REPO, submodules and all"

# Checkout
echo "+++ custom-checkout.sh BEGIN"
echo I am `whoami`
echo I am in dir `pwd`
cd $BUILDKITE_BUILD_CHECKOUT_PATH    # Just in case, I dunno, whatevs.

if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then
    echo "Pull request from a submod repo: check out aha master branch"
    git fetch -v --prune -- origin master
    git checkout -qf master
else
    echo "Push or PR from aha repo: check out requested aha branch"
    git fetch -v --prune -- origin $BUILDKITE_COMMIT
    git checkout -qf $BUILDKITE_COMMIT
fi


# If trigger came from a submod repo, we will do "pr" regressions.
# Otherwise, trigger came from aha repo push/pull and we just do "daily" regressions.
# We use commdir to pass information to other steps.
# THIS ASSUMES THAT ALL STEPS RUN ON SAME HOST MACHINE and thus see the same commdir!

echo "--- Determine whether to do daily or pr regressions"
if git checkout -qf $BUILDKITE_COMMIT; then
    echo "+++ UNSET DO_PR"
    echo "BUILDKITE_COMMIT found in aha repo, we will do daily regressions."
else
    echo "+++ SET DO_PR"
    echo "BUILDKITE_COMMIT not found in aha repo, we will do pr regressions."
    # FIXME could combine this with env-BNO temp file used by update-pr-repo.sh
    commdir=/var/lib/buildkite-agent/builds/DELETEME; mkdir -p $commdir;
    echo true > $commdir/DO_PR-${BUILDKITE_BUILD_NUMBER}
fi

echo "--- Check out appropriate AHA branch: $BUILDKITE_COMMIT, $DEV_BRANCH, or master"
cd $BUILDKITE_BUILD_CHECKOUT_PATH
# FIXME can delete DEV_BRANCH part once dev branch merges to master FIXME
DEV_BRANCH=remotes/origin/no-heroku
echo 'git checkout -qf $BUILDKITE_COMMIT || git checkout -qf $DEV_BRANCH || git checkout -qf master'; set -x
      git checkout -qf $BUILDKITE_COMMIT || git checkout -qf $DEV_BRANCH || git checkout -qf master

echo "--- PREP AHA REPO and all its submodules"; set -x
pwd
# E.g. CHECKOUT_PATH=/var/lib/buildkite-agent/builds/r7cad-docker-1/stanford-aha/aha-flow
cd $BUILDKITE_BUILD_CHECKOUT_PATH # Actually I think we're already there but whatevs

git submodule update --checkout # This is probably unnecessary but whatevs
git remote set-url origin https://github.com/StanfordAHA/aha
git submodule foreach --recursive "git clean -ffxdq"
git clean -ffxdq
set +x

echo "--- See if we need to update a submodule"
unset PR_FROM_SUBMOD

# PR_FROM_SUBMOD means build was triggered by foreign (non-aha) repo,
# i.e. one of the submods. The submod sends its commit hash BUT DOES
# NOT TELL US WHAT REPO IT IS. :(

# We detect this by attempting to fetch BUILDKITE_COMMIT from aha repo.
# Success means this is an aha-triggered build. Failure means we need to
# find what repo actually did trigger the commit.

echo git fetch -v --prune -- origin $BUILDKITE_COMMIT
if   git fetch -v --prune -- origin $BUILDKITE_COMMIT; then

    # Pretty sure we already did this, in pipeline.xml BDI step pre-checkout hook
    # But what the heck, let's do it again, don't break what is working already.
    git checkout -f $BUILDKITE_COMMIT
    echo "Found aha commit '$BUILDKITE_COMMIT'; no need to update submodule"

else
    echo '-------------------------------------------'
    echo 'REQUESTED COMMIT DOES NOT EXIST in aha repo'
    echo '(This must be a pull request from one of the submods)'
    echo 'Will checkout aha default branch'
    PR_FROM_SUBMOD=true

        echo "Aha branch '$AHA_DEFAULT_BRANCH' does not exist"
        echo "Fetching aha master branch"
        git fetch -v --prune -- origin master
        git checkout -f master

fi

set -x
git submodule sync --recursive
echo "--- git submodule update --init --recursive --force"
git submodule update --init --recursive --force
echo '--- git submodule foreach --recursive "git reset --hard"'
git submodule foreach --recursive "git reset --hard"
set +x

# update_repo=`git config --get remote.origin.url`

if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then
    echo "--- Update submodule '$PR_REPO_TAIL' w commit '$BUILDKITE_COMMIT'"
    (set -x; cd $PR_REPO_TAIL; git fetch origin && git checkout $BUILDKITE_COMMIT)
fi

echo "--- custom-checkout.sh END"

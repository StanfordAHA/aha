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





echo "+++ LINKLABELS"
set -x
# buildkite-agent annotate "hello"
# buildkite-agent annotate --style "info" "hello woild http://ibm.com" --context 1
# buildkite-agent annotate --style "warning"  "hello woild https://ibm.com" --context 2
# buildkite-agent annotate --style "success" "_hello woild_ [IBM](http://ibm.com)]" --context 3
# buildkite-agent annotate --style "error" "_hello woild_ [IBM](http://ibm.com)]" --context 4


if [ "BUILDKITE_PULL_REQUEST_REPO" ]; then
    # E.g.
    # BUILDKITE_PULL_REQUEST_REPO="https://github.com/StanfordAHA/lake.git"
    # BUILDKITE_PULL_REQUEST="166"
    # BUILDKITE_COMMIT=7c5e88021a01fef1a04ea56b570563cae2050b1f
    # ----------------
    # first7=  7c5e880
    # repo=    https://github.com/StanfordAHA/lake'
    # url_cm=  https://github.com/StanfordAHA/lake/commit/7c5...0b1f
    # url_pr=  https://github.com/StanfordAHA/lake/pull/166

    first7=`expr "$BUILDKITE_COMMIT" : '\(.......\)'`
    repo=`echo "$BUILDKITE_PULL_REQUEST_REPO" | sed 's/.git$//'`
    r=`echo "$repo" | sed 's/http.*github.com.//'`
    url_cm=${repo}/commit/${BUILDKITE_COMMIT}
    url_pr=${repo}/pull/${BUILDKITE_PULL_REQUEST}
    mdlink_cm="[${first7}](${url_cm})"
    mdlink_pr="[Pull Request #${BUILDKITE_PULL_REQUEST}](${url_pr})"

    cat <<EOF | buildkite-agent annotate --style "info" --context foo3
E3
This build was triggered by a pull request from ${r}
${mdlink_cm} (${mdlink_pr})
EOF

    cat <<EOF | buildkite-agent annotate --style "info" --context foo2
E2
This build was triggered by a pull request from ${r} ${mdlink_cm} (${mdlink_pr})
EOF
    cat <<EOF | buildkite-agent annotate --style "info" --context foo4
E1
PULL REQUEST FROM https://github.com/StanfordAHA/lake 
Corrected links: [7c5e880](https://github.com/StanfordAHA/lake/commit/7c5e88021a01fef1a04ea56b570563cae2050b1f) ([Pull Request #166](https://github.com/StanfordAHA/lake/pull/166))
EOF





# FAIL
#     cat <<EOF | buildkite-agent annotate --style "info" --context foo3
#     E3
#     PULL REQUEST FROM https://github.com/StanfordAHA/lake 
#     Corrected links: [7c5e880](https://github.com/StanfordAHA/lake/commit/7c5e88021a01fef1a04ea56b570563cae2050b1f) ([Pull Request #166](https://github.com/StanfordAHA/lake/pull/166))

#     cat <<EOF | buildkite-agent annotate --style "info" --context foo1
#     E1
#     PULL REQUEST FROM ${repo} 
#     Corrected links: ${mdlink_cm} (${mdlink_pr})

#     cat <<EOF | buildkite-agent annotate --style "info" --context foo0 --debug 9
#     E0
#     PULL REQUEST FROM ${repo} 
#     Corrected links: ${mdlink_cm} (${mdlink_pr})
    




fi
set +x

#     Corrected links: [${first7}](${url_cm}] ([Pull Request #${BUILDKITE_PULL_REQUEST}](${url_pr}))



echo "--- CHECKOUT FULL REPO, submodules and all"

# Checkout
echo "+++ custom-checkout.sh BEGIN"
echo I am `whoami`
echo I am in dir `pwd`
cd $BUILDKITE_BUILD_CHECKOUT_PATH    # Just in case, I dunno, whatevs.

# FIXME don't need this after heroku is gone! FIXME
# Heroku sets BUILDKITE_COMMIT to sha of aha master branch.
# We want to rewrite that to be the sha of submod repo that
# originally triggered the build.

if expr "$BUILDKITE_MESSAGE" : "PR from " > /dev/null; then
    echo "Found heroku, rewriting BUILDKITE_COMMIT";
    BUILDKITE_COMMIT=$FLOW_HEAD_SHA;
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
git remote set-url origin https://github.com/hofstee/aha
git submodule foreach --recursive "git clean -ffxdq"
git clean -ffxdq
set +x

# FIXME can of course delete this after heroku is gone FIXME
# Heroku always sets message to "PR from <repo>" with BUILDKITE_COMMIT="HEAD"
# so as to checkout aha master. Heroku also sends desired submod commit <repo>
# hash as env var FLOW_HEAD_SHA.  In this new regime, we set BUILDKITE_COMMIT
# as the desired submod commit, and auto-discover the repo that goes with the commit.

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

    # FIXME don't need if-then-else below after dev merges to master.
    # Use dev branch as default until it gets merged and deleted.
    AHA_DEFAULT_BRANCH=no-heroku
    echo "Meanwhile, will use default branch '$AHA_DEFAULT_BRANCH' for aha repo"
    if git fetch -v --prune -- origin $AHA_DEFAULT_BRANCH; then
        echo "Fetching aha branch '$AHA_DEFAULT_BRANCH'"
        git checkout -f $AHA_DEFAULT_BRANCH
    else
        echo "Aha branch '$AHA_DEFAULT_BRANCH' does not exist"
        echo "Fetching aha master branch"
        git fetch -v --prune -- origin master
        git checkout -f master
    fi
fi

set -x
git submodule sync --recursive
echo "--- git submodule update --init --recursive --force"
git submodule update --init --recursive --force
echo '--- git submodule foreach --recursive "git reset --hard"'
git submodule foreach --recursive "git reset --hard"
set +x

update_repo=`git config --get remote.origin.url`

# To find out what repo triggered the commit, we iterate through
# all the submodules and find which one can successfully checkout
# the desired BUILKITE_COMMIT.

# NOTE this is not necessary for pull requests, which embed the
# repo information as BUILDKITE_PULL_REQUEST. Push requests have
# no such mechanism however :(
# In general we don't process push requests from submodules, but
# this was useful for development etc.

if [ "$PR_FROM_SUBMOD" ]; then
    echo "--- Handle PR"
    echo "+++ Looking for submod commit $BUILDKITE_COMMIT"
    unset FOUND_SUBMOD
    for submod in garnet Halide-to-Hardware lassen gemstone canal lake hwtypes; do
        echo "--- - " Looking in submod $submod
        # --- THIS IS WHERE THE CHECKOUT HAPPENS ---
        (set -x; cd $submod; git fetch origin && git checkout $BUILDKITE_COMMIT) && FOUND_SUBMOD=true || echo "NOT " $submod
        [ "$FOUND_SUBMOD" ] && echo "--- -- FOUND " $submod
        [ "$FOUND_SUBMOD" ] && break
    done

    if [ "$FOUND_SUBMOD" ]; then
        echo "--- Updated submodule '$submod' w commit '$BUILDKITE_COMMIT'"
        update_repo=`cd $submod; git config --get remote.origin.url`
    else
        echo "ERROR could not find requesting submod"; exit 13
    fi
    set +x
else
    echo "--- NOT A PULL REQUEST"
fi

echo "--- custom-checkout.sh END"

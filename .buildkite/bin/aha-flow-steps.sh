# This file is designed to replace the existing aha-flow buildkite script at
# <https://buildkite.com/stanford-aha/aha-flow/settings/steps>.
# By moving the script to the repo, we can have it under version control, etc.

set +x
DEV_BRANCH=master  # I.e. not using a dev branch atm
export DEV_BRANCH=$DEV_BRANCH  # FIXME things break if DEV_BRANCH not set?

set +u;  # My code assumes unset vars are okay
echo "+++ Must have a (empty!) working directory"; set -x;
d=$BUILDKITE_BUILD_CHECKOUT_PATH;
/bin/rm -rf $d; mkdir -p $d; ls -ld $d; cd $d;

echo "--- CUSTOM CHECKOUT BEGIN"; set -x;
echo "Fast checkout w/ no submod loads (yet)";
aha_clone=$BUILDKITE_BUILD_CHECKOUT_PATH;
git clone https://github.com/StanfordAHA/aha $aha_clone; cd $aha_clone;

# My scripts don't deal well with a commit that's not a full hash!
if [ "$BUILDKITE_COMMIT" == "HEAD" ]; then
    BUILDKITE_COMMIT=`git rev-parse HEAD`; fi
if ! git checkout -q $BUILDKITE_COMMIT; then
    echo "Submod commit hash found, using aha master branch";
    git checkout -q $DEV_BRANCH || echo "No dev branch found, continuing w master..."; fi;

# git checkout -q $BUILDKITE_COMMIT || echo "Submod commit hash found, using aha master branch";
# git checkout -q $BUILDKITE_COMMIT || git checkout -q $DEV_BRANCH || echo "No dev branch found, continuing w master...";

# Note, /home/buildkite-agent/bin/status-update must exist on agent machine
# Also see ~steveri/bin/status-update on kiwi
echo "+++ Notify github of pending status"; ~/bin/status-update --force pending;
buildkite-agent pipeline upload .buildkite/pipeline.yml;
echo "--- CUSTOM CHECKOUT END"

################################################################################
# <https://buildkite.com/stanford-aha/aha-flow/settings/steps> should have just
# the bare bones required to load and run this setup script. Something like:
################################################################################
# env:
#   # DEV_BRANCH: master
#   DEV_BRANCH: offload-steps
#   AHA_REPO: https://raw.githubusercontent.com/StanfordAHA/aha
#   STEPSCRIPT: .buildkite/bin/aha-flow-steps.sh
# 
# # Must do commands in pre-checkout else get wrong BUILDKITE_MESSAGE
# steps:
# - label: ":pipeline:"
#   agents: { docker: true }
#   plugins:
#   - uber-workflow/run-without-clone:
#   - improbable-eng/metahook:
#       pre-checkout: |
#         udev=$$AHA_REPO/$$DEV_BRANCH/$$STEPSCRIPT
#         httpcode=`curl $$udev -o aha-flow-steps.sh -w '%{http_code}'`
#         if ! [ "$$httpcode" == 200 ]; then
#             echo "Cannot find steps in branch '$$DEV_BRANCH'; trying master instead"
#             curl $$AHA_REPO/master/$$STEPSCRIPT -o aha-flow-steps.sh
#         fi
#         source aha-flow-steps.sh
#   command: echo DONE  # (Breaks if no command)
################################################################################

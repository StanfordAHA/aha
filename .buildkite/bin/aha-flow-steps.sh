# https://buildkite.com/stanford-aha/aha-flow/settings/steps
# should have something like this:
# 
# env:
#     # DEV_BRANCH: master
#     DEV_BRANCH: offload-steps
# 
# steps:
# - label: ":pipeline:"
#   agents: { docker: true }
#   command: echo DONE
#   plugins:
#     # Turn off normal/slow repo+submods checkout b/c all we need is pipeline.yml
#     - uber-workflow/run-without-clone:
#     
#     # Even though we turned off cloning, I think there's a reasone why
#     # we do commands in pre-checkout phase, but I can't quite remember why...?
#     - improbable-eng/metahook:
#         pre-checkout: |
#             set -x
#             mkdir -p DELETEME-aha-flow-{$BUILDKITE_BUILD_NUMBER}
#             udev=https://github.com/StanfordAHA/aha/blob/$$DEV_BRANCH/aha-flow-steps.sh
#             umaster=https://github.com/StanfordAHA/aha/blob/master/aha-flow-steps.sh
#             httpcode=`curl $$udev -o $$TMPDIR/aha-flow-steps.sh`
#             if ! [ $httpcode == 200 ]; then
#                 echo "Cannot find steps in branch '$$DEV_BRANCH'; trying master instead"
#                 export DEV_BRANCH=master  # FIXME things break if DEV_BRANCH not set
#                 curl $$umaster -o $$TMPDIR/aha-flow-steps.sh
#             fi
#             set +x
#             source $$TMPDIR/aha-flow-steps.sh

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
grep conv2 .buildkite/pipeline.yml || echo not found oh no;
buildkite-agent pipeline upload .buildkite/pipeline.yml;
echo "--- CUSTOM CHECKOUT END"

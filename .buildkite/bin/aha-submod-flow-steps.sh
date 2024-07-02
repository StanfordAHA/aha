# This file is designed to replace the existing aha-flow buildkite script at
# <https://buildkite.com/stanford-aha/aha-submod-flow/settings/steps>.
# By moving the script to the repo, we can have it under version control, etc.

# To prevent github push events from triggering builds, set pipeline
# github settings to "Filter builds using a conditional" with:
#     build.pull_request.base_branch == "master"
# (https://buildkite.com/stanford-aha/aha-submod-flow/settings/repository)

set +u;  # My code assumes unset vars are okay

echo "+++ Must have a (empty!) working directory"; set -x;
d=$BUILDKITE_BUILD_CHECKOUT_PATH;
/bin/rm -rf $d; mkdir -p $d; ls -ld $d; cd $d

echo "--- CUSTOM CHECKOUT BEGIN"; set -x;
echo "Fast checkout w/ no submod loads (yet)";
aha_clone=$BUILDKITE_BUILD_CHECKOUT_PATH;
git clone https://github.com/StanfordAHA/aha $aha_clone; cd $aha_clone;

echo "Set BPPR_TAIL for later usage, e.g. BPPR_TAIL=canal";
export BPPR_TAIL=`echo "$BUILDKITE_PULL_REQUEST_REPO" | sed "s/.git\$//"` || echo fail;
url=$BPPR_TAIL
BPPR_TAIL=`echo "$BPPR_TAIL" | sed "s,http.*github.com/.*/,,"` || echo fail;

# Find submod commit hash; use url calculated above
# E.g. https://github.com/StanfordAHA/lake/pull/194
set -x;
curl $url/pull/$BUILDKITE_PULL_REQUEST > tmp;
grep 'oid=' tmp | tr -cd '[:alnum:]=\n' | head -n 1;
grep 'oid=' tmp | tr -cd '[:alnum:]=\n' | head -n 1 || echo OOPS;
submod_commit=`curl -s $url/pull/$BUILDKITE_PULL_REQUEST \
          | grep 'oid=' | tr -cd '[:alnum:]=\n' | head -n 1 \
          | sed 's/.*oid=\(.......\).*/\1/'`;
echo "found submod commit $submod_commit";
save_commit=$BUILDKITE_COMMIT;
export BUILDKITE_COMMIT=$submod_commit;

# Note, /home/buildkite-agent/bin/status-update must exist on agent machine
# Also see ~steveri/bin/status-update on kiwi
echo "+++ Notify github of pending status";
~/bin/status-update --force pending;
  
# 'update-pr-repo.sh' will use AHA_SUBMOD_FLOW_COMMIT to set up links and such
export BUILDKITE_COMMIT=$save_commit;
echo "Trigger aha-flow pipeline";
export AHA_SUBMOD_FLOW_COMMIT=$submod_commit;
          
# Note, /home/buildkite-agent/bin/pr_trigger.yml must exist on agent machine
# buildkite-agent pipeline upload .buildkite/pr_trigger.yml;
buildkite-agent pipeline upload ~/bin/pr_trigger.yml;
echo "--- CUSTOM CHECKOUT END";


##################################################################################
# <https://buildkite.com/stanford-aha/aha-submod-flow/settings/steps> should have
# just the bare bones required to load and run this setup script. Something like:
##################################################################################
# env:
#   # DEV_BRANCH: master
#   DEV_BRANCH: ci-cleanup
#   AHA_REPO: https://raw.githubusercontent.com/StanfordAHA/aha
#   STEPSCRIPT: .buildkite/bin/aha-submod-flow-steps.sh
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

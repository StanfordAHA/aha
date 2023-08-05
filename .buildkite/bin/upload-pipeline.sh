#!/bin/bash

# save and restore existing shell opts in case script is sourced
RESTORE_SHELLOPTS="$(set +o)"
set +u # nounset? not on my watch!
set +x # Extreme dev time is OVER

echo "--- BEGIN upload-pipeline.sh"

# Remote locations for pipeline, checkout scripts
# (Unique BUILD_NUMBER query at end of url prevents caching)
p_remote=pipeline.yml?$BUILDKITE_BUILD_NUMBER
c_remote=bin/custom-checkout.sh?$BUILDKITE_BUILD_NUMBER

# Where to put scripts (locally) when we find them
p_local=/tmp/aha-flow-$BUILDKITE_BUILD_NUMBER-pipeline.xml
c_local=/tmp/aha-flow-$BUILDKITE_BUILD_NUMBER-custom-checkout.sh

# Various places we might find pipeline.xml
u=https://raw.githubusercontent.com/StanfordAHA/aha
amaster=$u/master/.buildkite
acommit=$u/$BUILDKITE_COMMIT/.buildkite
adev=$u/no-heroku/.buildkite

# Establish baselines
curl -s --fail $amaster/$p_remote > $p_local
curl -s        $amaster/$c_remote > $c_local  # Okay (for now) if checkout.sh does not exist
echo Established default pipeline $p_local from aha master branch.

# ls /tmp/*/pre-command || echo nop
# cat -n /tmp/*/pre-command || echo nop

for i in 1; do
    echo "Heroku trigger? (Until we turn it off, heroku behaves as before.)"
    # Test this path by doing "git pull master" from a submodule
    if [ "$FLOW_HEAD_SHA" ]; then
        echo "Found heroku, will use pipeline from master, as before."
        break
    fi
    echo Not heroku, continue search for possible default override.

    # If acommit exists, trigger came from aha repo.
    # Test this path by doing "git push" from aha repo
    echo "Triggered by valid aha-repo commit? If so, use pipeline from that commit."
    if curl -sf $acommit/$p_remote > $p_local; then
       echo Using pipeline from commit $acommit
       echo downloading $acommit/$c_remote
       curl -s  $acommit/$c_remote > $c_local  # Okay (for now) if checkout.sh does not exist
       ls -l $c_local || echo no
       break
    fi
    echo "Not triggered by aha repo, must be a request from a submodule."
    echo "-----"

    echo "Override default w dev script if one exists"
    # Not heroku; not aha; this is the new stuff
    # Triggered by non-aha repo (i.e. just garnet for now)
    # Use dev pipe if exists, else stick with master
    # Test this path (for now) by doing a "git push" from garnet repo
    if curl -sf $adev/$p_remote > $p_local; then
       curl -sf $adev/$c_remote > $c_local; break
    fi
    echo Cannot find dev pipeline, will stay w master default.
done

echo "+++ DEBUG: What is up with r7cad-docker-5?"
set -x
d=/var/lib/buildkite-agent/builds/r7cad-docker-5/stanford-aha/aha-flow
ls -ld $d || echo no
echo "-----"
ls -la $d || echo no
echo "-----"
ls -laR $d | grep root || echo no
printf "===\n===\n===\n"
ls -la $d/temp/temp/ || echo no
echo "-----"
ls -ld $d/temp/temp/.TEST || echo no
printf "===\n===\n===\n"
set +x

# That's what's up.
# ls -la /var/lib/buildkite-agent/builds/r7cad-docker-5/stanford-aha/aha-flow
# buildkite-agent temp
# 
# ls -laR /var/lib/buildkite-agent/builds/r7cad-docker-5/stanford-aha/aha-flow | grep root
# root temp
# root .
# root .TEST

# # If temp subdir contains files owned by root, that's bad.
# # Delete the entire directory if this is found to be true.
# echo "+++ PURGE BAD TEMP FILES"
# for d in /var/lib/buildkite-agent/builds/*/stanford-aha/aha-flow/temp/; do
#     if (ls -laR $d | grep root); then
#         echo "WARNING found root-owned objects in $d"
#         set -x; /bin/rm -rf $d; set +x
#     fi
# done






echo "--- continue"
buildkite-agent pipeline upload $p_local

echo RESTORE SHELLOPTS
eval "$RESTORE_SHELLOPTS"

ls -l $c_local || echo ERROR cannot find $c_local

echo "--- END upload-pipeline.sh"

#!/bin/bash

# save and restore existing shell opts in case script is sourced
RESTORE_SHELLOPTS="$(set +o)"
set +u # nounset? not on my watch!

echo "--- upload-pipeline BEGIN"


set -x

# Unique BUILD_NUMBER query at end of url prevents caching
p=pipeline.yml?$BUILDKITE_BUILD_NUMBER
ptmp=/tmp/aha-flow-$BUILDKITE_BUILD_NUMBER-pipeline.xml
c=bin/custom-checkout.sh?$BUILDKITE_BUILD_NUMBER
ctmp=/tmp/aha-flow-$BUILDKITE_BUILD_NUMBER-custom-checkout.sh

# Various places we might find pipeline.xml
u=https://raw.githubusercontent.com/StanfordAHA/aha
amaster=$u/master/.buildkite
acommit=$u/$BUILDKITE_COMMIT/.buildkite
adev=$u/no-heroku/.buildkite

# Establish baselines. Okay (for now) if checkout.sh does not exist
curl -s --fail $amaster/$p > $ptmp; curl -s $amaster/$c > $ctmp
echo Established default pipeline foo

ls /tmp/*/pre-command || echo nop
cat -n /tmp/*/pre-command || echo nop

for i in 1; do set -x
    # Test this path by doing "git pull master" from a submodule
    [ "$FLOW_HEAD_SHA" ] && break    # (heroku uses pipeline from master)
    echo Not heroku, stay w default

    # curl -s $acommit/$p > $ptmp  && break || echo Not triggered by aha repo
    # If acommit exists, trigger came from aha repo. Okay (for now) if checkout.sh does not exist
    # Test this path by doing "git push" from aha repo
    if curl -sf $acommit/$p > $ptmp; then curl -s  $acommit/$c > $ctmp; break; fi
    echo Not triggered by aha repo

    # curl -s $adev/$p > $ptmp  && break || echo Cannot find dev pipeline
    # Not heroku; not aha; this is the new stuff
    # Triggered by non-aha repo (i.e. just garnet for now)
    # Use dev pipe if exists, else stick with master
    # Test this path (for now) by doing a "git push" from garnet repo
    if curl -sf $adev/$p > $ptmp; then curl -sf $adev/$c > $ctmp; break; fi
    echo Cannot find dev pipeline, will use master instead
done

buildkite-agent pipeline upload $ptmp

echo "--- RESTORE SHELLOPTS"; eval "$RESTORE_SHELLOPTS"
echo "--- upload-pipeline END"

#!/bin/bash

# what do i do? not much ackshully
# - emit some status info
# - (temporarily) find root-owned temp directories and expose them (!!!)
# - upload local (agent-specific) pipeline.yml

echo "--- BEGIN upload-pipeline.sh"

set +u     # nounset? not on my watch!
set +x     # Extreme dev time is OVER
shopt -s dotglob  # Else will not copy/remove dotfiles e.g. .buildkite/hooks :o

echo "I am here: `pwd`"
git status -buno | head -1  # E.g. "On branch no-heroku" or "HEAD detached at 3bf5dc7"


##############################################################################
##############################################################################
##############################################################################
# root-owned temp directories

# For awhile, pipeline.yml step "Onyx Integration Tests" was running a docker
# container with a local directory mounted as "/buildkite", and then doing
# a 'touch /buildkite/temp/.TEST' from inside the container. This creates
# a ROOT-OWNED UNREMOVABLE directory 'temp' and file 'temp/.TEST' in the
# host machine.

# This section of code is designed to remedy that.

# First we will look in all agent build dirs to see if the problem still exists.
baddirs=
echo "+++ CHECKING FOR BAD TEMP FILES"
for d in /var/lib/buildkite-agent/builds/*/stanford-aha/aha-flow/temp; do
    echo "Checking $d..."
    if (ls -laR $d | grep root 2> /dev/null); then
        baddirs="$baddirs $d"
    fi
done
echo "-----------------------------"

for d in $baddirs; do 
    printf "WARNING found root-owned objects in $d\n\n"
done
echo "-----------------------------"

# As an extreme measure, and at risk of destroying someone's in-progress build,
# we will move the offending directory to our DELETEME quarantine space.
for d in $baddirs; do 
    set -x
    mkdir -p /var/lib/buildkite-agent/builds/DELETEME/temp-$BUILDKITE_BUILD_NUMBER-$RANDOM
    # set -x; /bin/rm -rf $d; set +x
    repo=$(cd $d; cd ..; pwd)
    echo "DESTRUCTIVE PURGE of directory $repo..."
    # What are you, crazy? What if someone is using this repo???
    mv $repo /var/lib/buildkite-agent/builds/DELETEME/temp-$BUILDKITE_BUILD_NUMBER-$RANDOM/
    set +x
done
echo "-----------------------------"

# First delete what you can without being root
set -x
/bin/rm -rf /var/lib/buildkite-agent/builds/DELETEME/* || echo okay
set +x
echo "-----------------------------"


# FINALLY we will try and purge the DELETEME directory of root-owned trash
d=/var/lib/buildkite-agent/builds/DELETEME
echo "ROOT-OWNED OBJECTS in $d"
t=`find /var/lib/buildkite-agent/builds/DELETEME -user root 2> /dev/null` || echo okay
echo "$t"
echo "-----------------------------"


if [ "$t" ]; then
    echo "PURGING ROOT-OWNED OBJECTS in $d"

    set -x
    d=/var/lib/buildkite-agent/builds/DELETEME
    image=ubuntu
    container=buildkite-DELETEME-purge
    docker kill $container || echo okay   # Kill stray container if exists already

    docker pull ubuntu
    docker run -id --name $container --rm -v $d:/DELETEME:rw $image bash
    set +x

    function dexec { docker exec $container /bin/bash -c "$*"; }
    echo "BEFORE: "; dexec "cd DELETEME; ls"
    echo "--------------------------------------------"
    echo "PURGE"
    echo 'dexec "/bin/rm -rf /DELETEME/temp*"'
          dexec "/bin/rm -rf /DELETEME/temp*"
    echo "--------------------------------------------"
    echo "AFTER: "; dexec "cd DELETEME; ls"
    echo "--------------------------------------------"

    docker kill $container
fi


echo "--- Upload the pipeline"
set -x
buildkite-agent pipeline upload .buildkite/pipeline.yml
set +x

echo "--- END upload-pipeline.sh"
return || exit


##############################################################################
##############################################################################
##############################################################################
# TRASH

# NO, too paranoid
# echo RESTORE SHELLOPTS
# eval "$RESTORE_SHELLOPTS"

# echo "+++ where is custom-checkout?"; set -x
# cc_local=$MYTMP/aha-flow-$BUILDKITE_BUILD_NUMBER-custom-checkout.sh
# ls -l $cc_local || echo ERROR cannot find $cc_local


# echo "+++ DEBUG: What is up with r7cad-docker-5?"
# set -x
# d=/var/lib/buildkite-agent/builds/r7cad-docker-5/stanford-aha/aha-flow
# ls -ld $d || echo no
# echo "-----"
# ls -la $d || echo no
# echo "-----"
# ls -laR $d | grep root || echo no
# printf "===\n===\n===\n"
# ls -la $d/temp/temp/ || echo no
# echo "-----"
# ls -ld $d/temp/temp/.TEST || echo no
# printf "===\n===\n===\n"
# set +x
# 
# # That's what's up.
# # ls -la /var/lib/buildkite-agent/builds/r7cad-docker-5/stanford-aha/aha-flow
# # buildkite-agent temp
# # 
# # Ls -laR /var/lib/buildkite-agent/builds/r7cad-docker-5/stanford-aha/aha-flow | grep root
# # root temp
# # root .
# # root .TEST

# -----
# # Remote locations for pipeline, checkout scripts
# # (Unique BUILD_NUMBER query at end of url prevents caching)
# p_remote=pipeline.yml?$BUILDKITE_BUILD_NUMBER
# c_remote=bin/custom-checkout.sh?$BUILDKITE_BUILD_NUMBER
# 
# # Where to put scripts (locally) when we find them
# p_local=$MYTMP/aha-flow-$BUILDKITE_BUILD_NUMBER-pipeline.xml
# c_local=$MYTMP/aha-flow-$BUILDKITE_BUILD_NUMBER-custom-checkout.sh
# 
# # Various places we might find pipeline.xml
# u=https://raw.githubusercontent.com/StanfordAHA/aha
# amaster=$u/master/.buildkite
# acommit=$u/$BUILDKITE_COMMIT/.buildkite
# adev=$u/no-heroku/.buildkite
# 
# # Establish baselines
# curl -s --fail $amaster/$p_remote > $p_local
# curl -s        $amaster/$c_remote > $c_local  # Okay (for now) if checkout.sh does not exist
# echo Established default pipeline $p_local from aha master branch.
# 
# for i in 1; do
#     echo "Heroku trigger? (Until we turn it off, heroku behaves as before.)"
#     # Test this path by doing "git pull master" from a submodule
#     if [ "$FLOW_HEAD_SHA" ]; then
#         echo "Found heroku, will use pipeline from master, as before."
#         break
#     fi
#     echo Not heroku, continue search for possible default override.
# 
#     # If acommit exists, trigger came from aha repo.
#     # Test this path by doing "git push" from aha repo
#     echo "Triggered by valid aha-repo commit? If so, use pipeline from that commit."
#     if curl -sf $acommit/$p_remote > $p_local; then
#        echo Using pipeline from commit $acommit
#        echo downloading $acommit/$c_remote
#        curl -s  $acommit/$c_remote > $c_local  # Okay (for now) if checkout.sh does not exist
#        ls -l $c_local || echo no
#        break
#     fi
#     echo "Not triggered by aha repo, must be a request from a submodule."
#     echo "-----"
# 
#     echo "Override default w dev script if one exists"
#     # Not heroku; not aha; this is the new stuff
#     # Triggered by non-aha repo (i.e. just garnet for now)
#     # Use dev pipe if exists, else stick with master
#     # Test this path (for now) by doing a "git push" from garnet repo
#     if curl -sf $adev/$p_remote > $p_local; then
#        curl -sf $adev/$c_remote > $c_local; break
#     fi
#     echo Cannot find dev pipeline, will stay w master default.
# done

##############################################################################
# Um pretty sure $MYTMP/.buildkite/bin/custom-checkout.sh exists already.
# 
# 
# 
# # custom pipeline.xml expects to find:
# #   CHECKOUT: /tmp/aha-flow-$$BUILDKITE_BUILD_NUMBER-custom-checkout.sh
# # sourced as pre-checkout hook in step "Build Docker Image"
# 
# # Why not use that directly?
# # MYTMP is set by https://buildkite.com/stanford-aha/aha-flow/settings/steps env, see?
# cc_local=$MYTMP/aha-flow-$BUILDKITE_BUILD_NUMBER-custom-checkout.sh
# echo cp .buildkite/bin/custom-checkout.sh $cc_local
#      cp .buildkite/bin/custom-checkout.sh $cc_local
# 
# echo ls .buildkite
#      ls .buildkite

# NO, too paranoid
# # save and restore existing shell opts in case script is sourced
# RESTORE_SHELLOPTS="$(set +o)"

# It only takes two seconds to clone a new aha; no need to cache it here.
# set -x
# # Use MYTMP to pass information from one step to the next on same machine
# MYTMP=`eval echo $MYTMP` # Expand '/var/lib/buildkite-agent/builds/$BUILDKITE_BUILD_NUMBER'
# # test -e $MYTMP/aha-flow && /bin/rm -rf $MYTMP/aha-flow
# mkdir -p $MYTMP
# cp -rp $BUILDKITE_BUILD_CHECKOUT_PATH $MYTMP/aha-flow
# set +x


# # Don't delete yourself!
# mkdir -p /var/lib/buildkite-agent/builds/$BUILDKITE_AGENT_NAME/stanford-aha/aha-flow

# echo ls .buildkite
#      ls .buildkite

# # FIXME once we reach steady state, can delete this wackadoo check.
# # FIXME !remindme maybe delete in a month, today is 4 aug 2023
# # If temp subdir contains files owned by root, that's bad.
# # Delete the entire directory if this is found to be true.
# echo "+++ CHECKING FOR BAD TEMP FILES"
# for d in /var/lib/buildkite-agent/builds/*/stanford-aha/aha-flow/temp; do
#     echo "Checking $d..."
#     if (ls -laR $d | grep root); then
#         printf "WARNING found root-owned objects in $d\n\n"
# 
# This is probably gonna be trouble!!! Not deleting/moving this anymore.
# But the right thing is to do it on demand and only when absolutely necessary
#         set -x
#         mkdir -p /var/lib/buildkite-agent/builds/DELETEME/temp-$BUILDKITE_BUILD_NUMBER-$RANDOM
#         # set -x; /bin/rm -rf $d; set +x
#         repo=$(cd $d; cd ..; pwd)
#         # What are you, crazy? What if someone is using this repo???
#         mv $repo /var/lib/buildkite-agent/builds/DELETEME/temp-$BUILDKITE_BUILD_NUMBER-$RANDOM/
#         set +x
#     fi
# done
# echo "-----------------------------"


# ls -laR /var/lib/buildkite-agent/builds/DELETEME | grep root || echo okay
# /bin/rm -rf /var/lib/buildkite-agent/builds/DELETEME/* || echo okay


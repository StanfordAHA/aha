#!/bin/bash

# what do i do? not much ackshully
# - emit some status info
# - (temporarily) find root-owned temp directories and expose them (!!!)
# - upload local (agent-specific) pipeline.yml

echo "--- BEGIN upload-pipeline.sh"

set +u     # nounset? not on my watch!
set +x     # Extreme dev time is OVER

echo "I am here: `pwd`"
git status -buno | head -1  # E.g. "On branch no-heroku" or "HEAD detached at 3bf5dc7"

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

# shopt -s dotglob  # Else will not copy/remove dotfiles e.g. .buildkite/hooks :o

# ##############################################################################
# ##############################################################################
# ##############################################################################
# # root-owned temp directories
# 
# # For awhile, pipeline.yml step "Onyx Integration Tests" was running a docker
# # container with a local directory mounted as "/buildkite", and then doing
# # a 'touch /buildkite/temp/.TEST' from inside the container. This creates
# # a ROOT-OWNED UNREMOVABLE directory 'temp' and file 'temp/.TEST' in the
# # host machine.
# 
# # This section of code is designed to remedy that.
# 
# # First we will look in all agent build dirs to see if the problem still exists.
# baddirs=
# echo "+++ CHECKING FOR BAD TEMP FILES"
# for d in /var/lib/buildkite-agent/builds/*/stanford-aha/aha-flow/temp; do
#     echo "Checking $d..."
#     if (ls -laR $d | grep root 2> /dev/null); then
#         baddirs="$baddirs $d"
#     fi
# done
# echo "-----------------------------"
# 
# for d in $baddirs; do 
#     printf "WARNING found root-owned objects in $d\n\n"
# done
# echo "-----------------------------"
# 
# # As an extreme measure, and at risk of destroying someone's in-progress build,
# # we will move the offending directory to our DELETEME quarantine space.
# for d in $baddirs; do 
#     set -x
#     mkdir -p /var/lib/buildkite-agent/builds/DELETEME/temp-$BUILDKITE_BUILD_NUMBER-$RANDOM
#     # set -x; /bin/rm -rf $d; set +x
#     repo=$(cd $d; cd ..; pwd)
#     echo "DESTRUCTIVE PURGE of directory $repo..."
#     # What are you, crazy? What if someone is using this repo???
#     mv $repo /var/lib/buildkite-agent/builds/DELETEME/temp-$BUILDKITE_BUILD_NUMBER-$RANDOM/
#     set +x
# done
# echo "-----------------------------"
# 
# # First delete what you can without being root
# set -x
# /bin/rm -rf /var/lib/buildkite-agent/builds/DELETEME/* || echo okay
# set +x
# echo "-----------------------------"
# 
# 
# # FINALLY we will try and purge the DELETEME directory of root-owned trash
# d=/var/lib/buildkite-agent/builds/DELETEME
# echo "ROOT-OWNED OBJECTS in $d"
# t=`find /var/lib/buildkite-agent/builds/DELETEME -user root 2> /dev/null` || echo okay
# echo "$t"
# echo "-----------------------------"
# 
# 
# if [ "$t" ]; then
#     echo "PURGING ROOT-OWNED OBJECTS in $d"
# 
#     set -x
#     d=/var/lib/buildkite-agent/builds/DELETEME
#     image=ubuntu
#     container=buildkite-DELETEME-purge
#     docker kill $container || echo okay   # Kill stray container if exists already
# 
#     docker pull ubuntu
#     docker run -id --name $container --rm -v $d:/DELETEME:rw $image bash
#     set +x
# 
#     function dexec { docker exec $container /bin/bash -c "$*"; }
#     echo "BEFORE: "; dexec "cd DELETEME; ls"
#     echo "--------------------------------------------"
#     echo "PURGE"
#     echo 'dexec "/bin/rm -rf /DELETEME/temp*"'
#           dexec "/bin/rm -rf /DELETEME/temp*"
#     echo "--------------------------------------------"
#     echo "AFTER: "; dexec "cd DELETEME; ls"
#     echo "--------------------------------------------"
# 
#     docker kill $container
# fi

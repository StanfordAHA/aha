#!/bin/bash

HELP="
Usage:   restore-dot-git.sh <submod-name>
Example: test -e /aha/.git/modules/clockwork || $0 clockwork
"
if ! [ "$1" ]; then echo "$HELP"; exit 13; fi

AHA=/aha
submod=$1
dotgit=$AHA/.git/modules/$submod

if test -e $dotgit; then
    echo ""
    echo "  $submod metadata exists, so will not run '$0 $submod'"
    echo "  If you really want to do this, remove '$dotgit' and try again."
    echo ""
    exit
fi

echo "------------------------------------------------------------------------"
echo "--- $0 $1"
echo "--- Restoring .git metadata for submodule '$submod'"

echo ""
echo "--- Find desired 'official' submod hash"
cd $AHA

# Note "git submodule" not guaranteed to work here when/if
# git is updated to newer version. Instead, use 'git ls-tree'
git ls-tree HEAD $submod | awk '{print $3}'
submod_sha=$(git ls-tree HEAD $submod | awk '{print $3}')

# E.g. url=https://github.com/StanfordAHA/clockwork.git
echo ""
url=`git config --file=$AHA/.gitmodules submodule.$submod.url`
echo "--- Restore metadata from repo '$url'"

# Use timeout-and-retry method b/c netowrk is flaky
# git clone --bare "$url" $AHA/.git/modules/$submod

ntries=8; timeouts=(x 20 30 60 120 300 600 1200 1200)
clone_dest=$AHA/.git/modules/$submod

# Cleanup is necessary in case child process of a failed clone
# keeps clone-dest directory locked during attempted retry
function cleanup_after_failed_attempt {
    printf '\n\n'
    me=$$; kids=`pgrep -P $me`; grandkids=$(for k in $kids; do pgrep -g $k; done)
    for p in $grandkids $kids; do
        exists $p || continue
        echo CLEANUP kill $p; kill $p; tail --pid=$p -f /dev/null
    done
    echo CLEANUP /bin/rm -rf $clone_dest
    /bin/rm -rf $clone_dest || echo okay;
}

echo "[`date +"%H:%M"`] BEGIN clone w up to $ntries with timeout(s)=(${timeouts[@]:1})"
for i in `seq $ntries`; do
    FAIL=
    timeout=${timeouts[$i]}
    try_begin=`date +%s`
    echo -n "[`date +"%H:%M"`] Clone attempt $i/$ntries timeout $timeout "
    # cloney $timeout && break
    /bin/rm -rf $clone_dest
    timeout $timeout git clone --bare $url $clone_dest && break

    FAIL=True
    try_end=`date +%s`
    echo -n "[`date +"%H:%M"`] Clone attempt $i/$ntries timeout $timeout "
    printf "FAIL after $(($try_end-$try_begin)) seconds\n\n"; 
    cleanup_after_failed_attempt >& /dev/null
   done

# Convert bare repo into something useful, with a work tree
cd $AHA/$submod; git config --local --bool core.bare false

echo ""
echo "--- Restore '$submod' branch '$submod_sha'"
cd $AHA/$submod; git checkout -f $submod_sha

echo ""
echo "--- Remove unnecessary local branches"
git for-each-ref --format '%(refname:short)' refs/heads \
   | egrep -v "^(master|main)$" \
   | xargs git branch -D

echo ""
echo "--- Restore remote-branch access"
set -x
cd $AHA/$submod
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
git fetch -p
set +x

echo ""
echo "+++ DONE"
printf "\ngit status\n"; git status -uno
printf "\ngit branch\n"; git branch

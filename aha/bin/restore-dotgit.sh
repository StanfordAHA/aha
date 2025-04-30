#!/bin/bash

HELP="
Usage:   restore-dot-git.sh <submod-name>
Example: test -e /aha/.git/modules/clockwork || $0 clockwork
"
if ! [ "$1" ]; then echo "$HELP"; exit 13; fi

submod=$1
dotgit=/aha/.git/modules/$submod

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
#  999dc896fc716f57e539f8819e4436a1b4d5c7bc clockwork (detailed_timing)
# submod_sha=999dc896f
cd /aha
git submodule | grep $submod | cut -b 2-1000
git submodule | grep $submod | cut -b 2-10
submod_sha=`git submodule | grep $submod | cut -b 2-10`

# E.g. url=https://github.com/StanfordAHA/clockwork.git
echo ""
url=`git config --file=/aha/.gitmodules submodule.$submod.url`



##############################################################################
##############################################################################
##############################################################################
echo "--- Restore metadata from repo '$url'"
git clone --bare "$url" /aha/.git/modules/$submod

ntries=8; timeouts=(x 20 30 60 120 300 600 1200 1200)
clone_dest=/aha/.git/modules/$submod

function cleanup {
    printf '\n\n'
    me=$$; kids=`pgrep -P $me`; grandkids=$(for k in $kids; do pgrep -g $k; done)
    for p in $grandkids $kids; do
        exists $p || continue
        echo CLEANUP kill $p; kill $p; tail --pid=$p -f /dev/null
    done
    echo CLEANUP /bin/rm -rf $tmp
    /bin/rm -rf $tmp || echo okay;
}
# function prep { /bin/rm -rf $tmp; mkdir -p $tmp/.git/modules; }
# function cloney { prep; timeout $1 git clone --bare $url $tmp/cw; }

echo "[`date +"%H:%M"`] BEGIN clone w up to $ntries with timeout(s)=(${timeouts[@]:1})"

   for i in `seq $ntries`; do

       FAIL=
       timeout=${timeouts[$i]}
       try_begin=`date +%s`
       echo -n "[`date +"%H:%M"`] Clone attempt $i/$ntries timeout $timeout "
       # cloney $timeout && break
       /bin/rm -rf $clone_dest
       timeout $timeout git clone --bare $url $clone_dest; }

       FAIL=True
       try_end=`date +%s`
       echo -n "[`date +"%H:%M"`] Clone attempt $i/$ntries timeout $timeout "
       printf "FAIL after $(($try_end-$try_begin)) seconds\n\n"; 
       cleanup >& /dev/null
   done
##############################################################################
##############################################################################
##############################################################################




# Convert bare repo into something useful, with a work tree
cd /aha/$submod; git config --local --bool core.bare false

echo ""
echo "--- Restore '$submod' branch '$submod_sha'"
cd /aha/$submod; git checkout -f $submod_sha

echo ""
echo "--- Remove unnecessary local branches"
git for-each-ref --format '%(refname:short)' refs/heads \
   | egrep -v "^(master|main)$" \
   | xargs git branch -D

echo ""
echo "--- Restore remote-branch access"
set -x
cd /aha/$submod
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
git fetch -p
set +x

echo ""
echo "+++ DONE"
printf "\ngit status\n"; git status -uno
printf "\ngit branch\n"; git branch

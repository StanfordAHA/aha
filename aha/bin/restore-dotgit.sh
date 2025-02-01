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
echo "--- Restore metadata from repo '$url'"
git clone --bare "$url" /aha/.git/modules/$submod

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

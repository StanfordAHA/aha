#!/bin/bash

sq="'" # Handle for single-quote character
HELP='
DESCRIPTION:
  Tells how far each submodule is from its respective master.
  Must be run from aha repo root.

EXAMPLE:
  % cd $AHA_REPO; aha/bin/aha-fresh.sh

  # Legend: Distance "n (a,b)" means submodule is <a> commits
  # ahead and <b> commits behind the submodule'$sq's master branch.

  lake                 5369a4c    356 (a0,b356)       StanfordAHA/lake
  clockwork            544e1de    316 (a0,b316)       dillonhuff/clockwork
  magma                266aaee    259 (a259,b0)       phanrahan/magma
  ...
  garnet               c22e8a4      0 (a0,b0)         stanfordaha/garnet
  cosa                 141be4b      0 (a0,b0)         cristian-mattarei/cosa
  BufferMapping        8ef4117      0 (a0,b0)         joyliu37/BufferMapping
'
[ "$1" == "--help" ] && echo "$HELP" && exit


DBG=notnull   # debug
DBG=''        # no debug

[ "$DBG" ] && echo '!!! DEBUGGING ON !!!'

[ "$1" == "--debug" ] && DBG=notnull
[ "$1" == "--debug" ] && shift

[ "$1" == "--token" ] && token='-H "Authorization: Bearer '$2'"'
[ "$1" == "--token" ] && shift

# git remote get-url origin
# - on kiwi, it returns "https:steveri:<...>/StanfordAHA/aha.git"
# - indside docker, it returns "https://github.com/StanfordAHA/aha"


# ERROR if script not run from correct directory (i.e. cloned aha repo)
if ! (git remote get-url origin | grep 'StanfordAHA/aha' > /dev/null); then
    echo Must be in aha repo for this to work, e.g.
    echo "(cd /nobackup/steveri/github/aha; $0)"
    exit 13
fi

# Get the commit hash of each submodule and place it
# in an ordered list of `$ncommits` elements e.g.

# { 8ef41175ab512bf0938283beb65d099935522990 52a1e2f96153b06687c21b958ded9bee82a10dcf ... }

commits=(`git submodule status | sed s/.// | awk '{print substr($1,1,8)}'`)
ncommits=${#commits[@]}
[ "$DBG" ] && echo Found ${#commits[@]} commits
[ "$DBG" ] && (echo ${commits[@]} | fold -s -w 82; echo "")

# Build a similar list for the names of the submodules e.g.
# { BufferMapping Halide-to-Hardware MetaMapper archipelago ast_tools canal ... }
names=(`git submodule status | sed s/.// | awk '{print $2}'`)
nnames=${#names[@]}
[ "$DBG" ] && echo Found ${#names[@]} submodules
[ "$DBG" ] && (echo ${names[@]} | fold -s; echo "")

function main {
  DBG=$1
  find_distance_header
  i=0; while [ $i -lt $ncommits ]; do

    # E.g. n = "canal" and c = "86d2934874fbe8c2f2461d36472b59d02edfd6c"
    n=${names[$i]}; c=${commits[$i]}; 
    # [ "$DBG" ] && printf "%02d %s %s\n" $i $c $n

    if ! line=`find_distance $n $c`; then
        echo "$line"
        exit 13
    fi

    echo "$line"
    all_lines=`printf "%s\n%s" "$line" "$all_lines"`

    ((i+=1))
    [ $i -gt 2 ] && [ "$DBG" ] && break

    [ $i -gt 100 ] && echo Too many commits
    [ $i -gt 100 ] && exit 13
    # echo ""; echo ""; echo ""; read -p "Continue [yn]? "
  done



  echo ""; echo "SORTED BY BADNESS"
  echo "$all_lines" | sort -k3 -rn
}

function find_distance_header {
cat <<EOF

# Legend: Distance "n (a,b)" means submodule is <a> commits
# ahead and <b> commits behind the submodule's master branch.
# 
# SUBMODULE          VERSION   DIST (ahead,behind)  REPO
EOF
}

# Given a stdin stream such that "grep _by" includes e.g.
#   "ahead_by": 2,
#   "behind_by": 0,
# return "2 0"

function ahead_behind { grep _by | awk -F '[:,]' '{print $2}' ; }

# Given a submodule and a commit hash, find how
# far ahead or behind it is vs. master HEAD
# 
# Example: find_distance MetaMapper f8b3399a

function find_distance {
    DBG=1   # debug
    DBG=    # no debug
    submod=$1; commit=$2

    # E.g. "https://github.com/rdaly525/MetaMapper"
    url=`git config --file .gitmodules submodule.$submod.url`

    # E.g. "rdaly525/MetaMapper"
    REPO=`echo $url | sed 's/https...github.com.//' | sed 's/.git$//' `


    # [ "$DBG" ] && echo gh api --paginate repos/$REPO/compare/$commit...master

    # ahead_behind=(0 25)
    gh="repos/$REPO/compare/$commit...master"
    # ahead_behind=(`gh api $gh | jq ".ahead_by,.behind_by"`)
    # ahead_behind=(`curl -s https://api.github.com/$gh | jq ".ahead_by,.behind_by"`)
    ahead_behind=(`curl -s $token https://api.github.com/$gh | ahead_behind`)

    if [ "$DBG" ]; then
      echo ${ahead_behind[@]}
      echo ahead  ${ahead_behind[0]}
      echo behind ${ahead_behind[1]}
    fi

    ahead=${ahead_behind[0]}
    behind=${ahead_behind[1]}

    if [ "$ahead" == "" ]; then
        echo Oops something ripped. > /dev/stderr
        echo curl -s https://api.github.com/$gh |& fold -sw 80 | head > /dev/stderr
        curl -s https://api.github.com/$gh |& fold -sw 80 | head > /dev/stderr
        exit 13
    fi

    distance=$(($ahead + $behind))
    [ "$DBG" ] && echo distance $distance

    ab=`printf "(a%d,b%d)" $ahead $behind`
    c7=`echo $commit | cut -b 1-7`

    #   SUBMODULE        VERSION     DIST (ahead,behind)  REPO
    # MetaMapper         f8b3399       25 (a0,b25)        rdaly525/MetaMapper

    printf "%-18s   %s %6d %-10s      %s\n" $submod $c7 $distance "$ab" $REPO
}

main $DBG
exit

#!/bin/bash
# set -x
# Timing
echo "BEGIN $(date)"
t_begin=$(date +%s)  # 1664872377

# Quick error check
repo=$(basename $(git remote get-url origin) | cut -d. -f1)
if ! test "$repo" = "aha"; then
    echo "ERROR must invoke script from within aha repo directory"
    exit 13
fi

# Populate the submodules

# Use 'git ls-tree' to list the submods, it works even when .git file(s) are corrupted
# "submods" should look like:
#   8ef41175ab512bf0938283beb65d099935522990 BufferMapping
#   9dabe69af0e5445401aafc48bc654a27beea5550 Halide-to-Hardware
#   ...
submods=$(git ls-tree HEAD | grep commit | awk '{print $3,$4}')

# Use '--reset' to delete all submods and start over maybe
if [ "$1" == "--reset" ]; then
    echo "# Cut'n'paste"
    echo "$submods" | while read line; do
        s=$(echo $line | awk '{print $2}')
        echo /bin/rm -rf aha/"{.git/modules/$s,$s}"
    done
    exit
fi

function DBG { false; }
function get_submod {
    # Search for existing submod. If found, copy it. Else,
    # record its name in a 'fails' list i.e. fails="clockwork sam"

    s=$1  # E.g. 'Buffermapping'
    c=$2  # E.g. '8ef41175ab512bf0938283beb65d099935522990'
    c8=$(echo $c | cut -b 1-8)  # E.g. '8ef41175'

    # Handle error conditions

    pwd
#     if ! test $(basename $PWD) = aha; then
#         echo "ERROR script must be invoked from inside aha directory"; return


    if test -e $s/.git; then
        echo "Submod '$s' already exists; not updating '$s'"; return
    fi

    # Search all dirs that might have cached info
    # echo "Looking for $c in agent cache(s)"
    for d in /var/lib/buildkite-agent/builds/*/stanford-aha/aha-flow; do

        # Skip squirrely repos w/no submod info
        test -e $d/.git/modules || continue

        # Find SHA for submod $s in the target cache
        cached=$(cd $d; git ls-tree HEAD $s | awk '{print $3}')
        if test "$cached" = "$c"; then
            # echo "Copying $s::$c8 from dir $d"
            dtrunc=$(echo $d | sed 's/.stanford.*//')
            printf " - Copying %-27s from $dtrunc\n" "$c8 $s"
            cp -rp $d/$s .


            if test -e $d/.git/modules/$s; then cp -rp $d/.git/modules/$s .git/modules
            else
                # DBG && echo "  - cannot find .git/modules/$s, maybe that's okay"
                echo "  - cannot find .git/modules/$s"
                echo "  - creating dummy .git/modules/$s, this might be terrible FIXME"
                mkdir -p .git/modules/$s
            fi


            return
        fi
    done    
    printf "\n\nCannot find cache for $s $c, must use backup/slow method\n"
    git submodule update --checkout $s
    (cd $s; git clean -ffxdq; git submodule foreach --recursive "git clean -ffxdq")




#     fails="$(echo $fails $s)"
#     echo fails=$fails
}
function DBG { false; }

            # cp -rp $d/.git/modules/$s .git/modules >& /dev/null || echo okay
# Found pono::b243cef7 in dir /var/lib/buildkite-agent/builds/khaki-1/stanford-aha/aha-flow

mkdir -p .git/modules  # A secret tool that will help us later
echo "$submods" | while read line; do
    linearray=($line)
    DBG && printf "\nget_submod ${linearray[1]} ${linearray[0]}\n"
    get_submod ${linearray[1]} ${linearray[0]}
done

# Timing
printf "END $(date)\n"
t_end=$(date +%s)  # 1664872377
function time_elapsed {
    # ns=$(($t_end - $t_begin))
    ns=$(($2 - $1))
    # nh=$(($ns/3600)); ns=$(($ns%3600))
    nm=$(($ns/60)); ns=$(($ns%60))
    # printf "%2dh %02dm %02ds" $nh $nm $ns
    printf "%4dm %02ds" $nm $ns
}
echo "TIME $(time_elapsed $t_begin $t_end)"

exit

s=BufferMapping
c=8ef41175ab512bf0938283beb65d099935522990
get_submod $s $c
exit


########################################################################
# TRASH
# 
#     echo "--- Processing failed submods '$fails'"
#     for submod in $fails; do
#         echo "  - processing $submod"
#         echo "  - searching cached info for submod commit number"
#         
#     done

#     FOUND IT! in dir /var/lib/buildkite-agent/builds/r8cad-docker-1/stanford-aha/aha-flow/BufferMapping
#     + cp -rp /var/lib/buildkite-agent/builds/r8cad-docker-1/stanford-aha/aha-flow/BufferMapping .
#     + mkdir -p .git/modules
#     ++ dirname /var/lib/buildkite-agent/builds/r8cad-docker-1/stanford-aha/aha-flow/BufferMapping
#     + subdir=/var/lib/buildkite-agent/builds/r8cad-docker-1/stanford-aha/aha-flow/.git/modules
#     + cp -rp /var/lib/buildkite-agent/builds/r8cad-docker-1/stanford-aha/aha-flow/.git/modules/BufferMapping .git/modules
#     + return
#     + exit

# pwd
# echo Now do:
# echo cp -rp $d .
# echo ls $s/.git
# echo mkdir -p .git/modules
# subdir=$(dirname $d)/.git/modules
# echo cp -rp $subdir/$s .git/modules


########################################################################
# TRASH
# 
# # TODO these must be treated differently maybe
# # git submodule status | egrep ^+ | sed 's/^.//'
# 
# # FOUND IT! in dir /var/lib/buildkite-agent/builds/r8cad-docker-1/stanford-aha/aha-flow/BufferMapping
# 
# #     echo -n $(echo $f | sed 's/.*builds..//;s/.stanford.*//'); \
# #     (cd $(dirname $f); git rev-parse HEAD); done
# 
# # for f in /var/lib/buildkite-agent/builds/*/stanford-aha/aha-flow/*/.git; do \
# #     (cd $(dirname $f); git rev-parse HEAD)
# 
# # git clone https://github.com/StanfordAHA/aha $aha_clone
# 
# # /home/steveri/0bugs/2504-bugs.txt:# GIT_TRACE=1 GIT_TRANSFER_TRACE=1 GIT_CURL_VERBOSE=1 
# # 
# # git clone git@github.com:github/debug-repo /tmp/debug-repo-ssh
# # git clone git@github.com:StanfordAHA/aha


#         # test -e $d/.git/modules/$s || continue
#         c2=FAIL; function is_backup { false; }
#         if test -e $d/.git/modules/$s; then
#             c2=$(cd $d/$s; git rev-parse HEAD)
#         elif test -e $d/.my-submod-list; then
#             echo "Cannot find '.git/modules/$s'; checking '.my-submod-list'"
#             c2=$(egrep " $s\$" $d/.my-submod-list | egrep ^- | sed 's/^.//; s/ .*//')
#             function is_backup { true; }
#         fi
#         # c2=$(cd $d/$s; git rev-parse HEAD)
#         if test "$c2" = "$c"; then
#             c8=$(echo $c | cut -b 1-8)
#             echo "Found '$s $c8' in dir $d"
#             set -x
#             cp -rp $d/$s .
#             is_backup || cp -rp $d/.git/modules/$s .git/modules
#             set +x
#             return
#         fi
#     done    
# 
# 
#     # echo "ERROR did not find existing $s $c; you'll have to do a submod init maybe"
#     echo "Cannot find existing $s $c"

# get_submod Halide-to-Hardware 9dabe69af0e5445401aafc48bc654a27beea5550
# echo fails=$fails
# exit

# if true; then
#     dba=/tmp/deleteme-bsi-aha
#     mkdir -p $dba
#     cd $dba
# fi

# function reuse_existing_aha { true; }
# # function reuse_existing_aha { false; }
# if ! reuse_existing_aha; then
#     if test -e aha; then
#         echo "Dir aha already exists; please delete/move it and try again"
#         exit 13
#     fi
#     # Clone the repo
#     git clone https://github.com/StanfordAHA/aha
# fi
# cd aha


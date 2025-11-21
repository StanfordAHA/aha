#!/bin/bash
# set -x
# Timing
echo "BEGIN $(date)"
t_begin=$(date +%s)  # 1664872377

# Quick error check
repo=$(basename $(git remote get-url origin) | cut -d. -f1)
if ! test "$repo" = "aha"; then
    # git clone https://github.com/StanfordAHA/aha
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

# Use this to test slow path maybe
if true; then
  submods=$(echo "$submods" | sed 's/.*voyager/00000000000000000000000000000000 voyager/')
  echo "$submods"
fi

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

    # Don't touch existing initialized submodules
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

            # Copy submodule contents
            dtrunc=$(echo $d | sed 's/.stanford.*//')
            printf " - Copying %-27s from $dtrunc\n" "$c8 $s"
            cp -rp $d/$s .

            # Copy submodule metadata if it exists
            if test -e $d/.git/modules/$s; then
                cp -rp $d/.git/modules/$s .git/modules
            else
                # Things break w/o the dummy
                echo "  - cannot find .git/modules/$s"
                echo "  - creating dummy .git/modules/$s, this might be terrible"
                mkdir -p .git/modules/$s
            fi
            return
        fi
    done

    # Slow-initialize recalcitrant submodules
    printf "\n\nCannot find cache for $s $c, must use backup/slow method\n"
    echo "... git submodule update --init --recursive --force $s ..."
    git submodule update --init --recursive --force $s
    (cd $s; git clean -ffxdq; git submodule foreach --recursive "git clean -ffxdq")
    git submodule sync --recursive $s
    echo "... git reset --hard $s recursively ..."
    (cd $s; git reset --hard; git submodule foreach --recursive "git reset --hard")
}
function DBG { false; }

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

# s=BufferMapping
# c=8ef41175ab512bf0938283beb65d099935522990
# get_submod $s $c

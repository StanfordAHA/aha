#!/bin/bash

########################################################################
# TODO
# - copy refs to 
# - --4x2 or something maybe
# - or maybe "rtl-gold-check <amber|onyx> <--4x2 | --32x16>"


########################################################################
# --help switch

cmd=rtl-gold-check.sh
cmd=$0

HELP="
DESCRIPTION: Builds RTL for a 4x2 amber grid, compares to reference build.

USAGE (default is "--local"):
   $cmd --amber  # Build and compare amber RTL
   $cmd --onyx   # Build and compare onyx RTL

EXAMPLE
   $cmd --amber && echo PASS || echo FAIL

"
[ "$1" == "--help" ] && echo "$HELP" && exit


# E.g. if script is "$GARNET_HOME/tests/test_amber_rtl_build/amber-rtl-build-check.sh"
# then scriptdir is "$GARNET_HOME/tests/test_amber_rtl_build"
scriptpath=$0
scriptpath=`readlink $scriptpath || echo $scriptpath`  # Full path of script dir
scriptdir=${scriptpath%/*}  # E.g. "build_tarfile.sh" or "foo/bar"

# Assumes script home is e.g. $AHA_REPO/aha/bin/

export GARNET_HOME=`cd $scriptdir/../../garnet; pwd`
echo "--- Found GARNET_HOME=$GARNET_HOME"

##############################################################################
# Work in a safe space I guess?
mkdir -p tmp-rtl-gold-check
cd       tmp-rtl-gold-check


########################################################################
# Always debug (for now). Later maybe:
# Use "-v" as first arg if want extra debug info
# [ "$1" == "-v" ] && shift && set -x

# width=32  # slow 32x16
width=4     # quick 4x2
height=$((width/2))




echo '--- RTL test BEGIN' `date`

# Default (for now)
export WHICH_SOC=amber

[ "$1" == "--amber" ] && export WHICH_SOC=amber

    # Use garnet's "gen_rtl.sh" to build a docker environment and use that to build the RTL

    export array_width=$width
    export array_height=$height
    export glb_tile_mem_size=256
    export num_glb_tiles=16
    export pipeline_config_interval=8
    export interconnect_only=False
    export glb_only=False
    export soc_only=False
    export PWR_AWARE=True
    export use_container=True

    # export use_local_garnet=True
    export use_local_garnet=False # for now

    export save_verilog_to_tmpdir=False
    export rtl_docker_image=default

    # (gen_rtl.sh copies final design.v to "./outputs" subdirectory)

    mkdir -p outputs
    $GARNET_HOME/mflowgen/common/rtl/gen_rtl.sh
    # mv outputs/design.v .


printf "\n"
echo "+++ Compare result to reference build"

# Reference designs are gzipped to save space
ref=garnet-4x2.v
test -f $ref && rm $ref
cp $scriptdir/ref/$ref.gz .; gunzip $ref.gz
f1=outputs/design.v; f2=$ref

# Need 'sed s/unq...' to handle the case where both designs are
# exactly the same but different "unq" suffixes e.g.
#     < Register_unq3 Register_inst0 (
#     > Register_unq2 Register_inst0 (
function vcompare { sort $1 | sed 's/,$//' | sed 's/unq[0-9*]/unq/' | sed '/^\s*$/d'; }

printf "\n"
echo "Comparing `vcompare $f1 | wc -l` lines of $f1"
echo "versus    `vcompare $f2 | wc -l` lines of $f2"
printf "\n"

echo "diff $f1 $f2"
ndiffs=`diff -Bb -I Date <(vcompare $f1) <(vcompare $f2) | wc -l`

if [ "$ndiffs" != "0" ]; then

    # ------------------------------------------------------------------------
    # TEST FAILED

    printf "Test FAILED with $ndiffs diffs\n\n"
    printf "Top 40 diffs:"
    diff -I Date <(vcompare $f1) <(vcompare $f2) | head -40
    exit 13
fi

echo "Test PASSED"




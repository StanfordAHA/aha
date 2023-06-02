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

# ##############################################################################
# # Work in a safe space I guess? => NO it just does a 'cd /aha' later :(
# mkdir -p tmp-rtl-gold-check
# cd       tmp-rtl-gold-check


########################################################################
# Always debug (for now). Later maybe:
# Use "-v" as first arg if want extra debug info
# [ "$1" == "-v" ] && shift && set -x

# width=32  # slow 32x16
width=4     # quick 4x2
height=$((width/2))




echo '--- RTL test BEGIN' `date`

# if [ "$1" == "--amber" ]; then
if [ 1 ]; then
    export WHICH_SOC=amber

    # Update docker to match necessary amber environment
    $GARNET_HOME/mflowgen/common/rtl/gen_rtl.sh -u | tee tmp-amber-updates.sh
    source tmp-amber-updates.sh
fi

    ########################################################################
    ########################################################################
    ########################################################################

    # FIXME should really use garnet's gen_rtl.sh to generate the RTL
    # This would require some kind of --no-docker flag for gen_rtl.sh or some such...

    # RTL-build flags
    flags="--width $width --height $((width/2)) --pipeline_config_interval 8 -v --glb_tile_mem_size 256"
    echo "FLAGS: $flags"

    # FIXME this makes a big mess in top-level dir /aha
    # Why not build in a subdir e.g. tmp-rtl-gold-check? (Would probably break a lot of things.)

    # Prep/clean
    cd /aha
    rm -rf garnet/genesis_verif
    rm -f  garnet/garnet.v

    # Build new rtl
    export WHICH_SOC='amber'
    source /aha/bin/activate; # Set up the build environment
    aha garnet $flags

    # Assemble final design.v
    cd /aha/garnet
    cp garnet.v genesis_verif/garnet.v
    cat genesis_verif/* > design.v
    cat global_buffer/systemRDL/output/glb_pio.sv >> design.v
    cat global_buffer/systemRDL/output/glb_jrdl_decode.sv >> design.v
    cat global_buffer/systemRDL/output/glb_jrdl_logic.sv >> design.v
    cat global_controller/systemRDL/output/*.sv >> design.v

    # For better or worse: I put this in gen_rtl.sh
    # Hack it up! FIXME should use same mechanism as onyx...define AO/AN_CELL
    # Also see: garnet/mflowgen/common/rtl/gen_rtl.sh, gemstone/tests/common/rtl/{AN_CELL.sv,AO_CELL.sv}
    cat design.v \
        | sed 's/AN_CELL inst/AN2D0BWP16P90 inst/' \
        | sed 's/AO_CELL inst/AO22D0BWP16P90 inst/' \
              > /tmp/tmp.v
    mv -f /tmp/tmp.v design.v

printf "\n"
echo "+++ Compare result to reference build"

# Reference designs are gzipped to save space
ref=garnet-4x2.v
test -f $ref && rm $ref
cp $scriptdir/ref/$ref.gz .; gunzip $ref.gz
f1=design.v; f2=$ref

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




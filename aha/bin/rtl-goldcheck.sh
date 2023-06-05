#!/bin/bash

########################################################################
# TODO want option to run 32x16 run maybe?
# - --4x2 or something maybe
# - or maybe "rtl-gold-check <amber|onyx> <--4x2 | --32x16>"


########################################################################
# --help switch

cmd=$0

HELP="
DESCRIPTION: Builds RTL for a 4x2 amber grid, compares to reference build.

USAGE (default is "--local"):
   $cmd amber  # Build and compare amber RTL
   $cmd onyx   # Build and compare onyx RTL

EXAMPLE
   $cmd amber && echo PASS || echo FAIL

"
[ "$1" == "--help" ] && echo "$HELP" && exit

########################################################################
# Pretty sure this only works inside a docker container :(
if ! test -e aha; then
  echo 'ERROR cannot find root directory "/aha"'
  echo 'Must be inside aha docker container for script to work'
  exit 13
fi

# export GARNET_HOME=`cd $scriptdir/../../garnet; pwd`
export GARNET_HOME=/aha/garnet
echo "--- Found GARNET_HOME=$GARNET_HOME"


# ##############################################################################
# # Work in a safe space I guess? => NO it just does a 'cd /aha' later :(
# mkdir -p tmp-rtl-gold-check; cd       tmp-rtl-gold-check


# width=32  # slow 32x16
width=4     # quick 4x2
height=$((width/2))

# FIXME should really use garnet's gen_rtl.sh to generate the RTL and flags etc.
# This would require some kind of --no-docker flag for gen_rtl.sh or some such...

# RTL-build flags
flags="--width $width --height $height --pipeline_config_interval 8 -v --glb_tile_mem_size 256"

# amber or onyx?
if [ "$1" == "amber" ]; then
    export WHICH_SOC=amber

    # Update docker to match necessary amber environment
    $GARNET_HOME/mflowgen/common/rtl/gen_rtl.sh -u | tee tmp-amber-updates.sh
    bash -c 'set -x; tmp-amber-updates.sh'

    ref=garnet-4x2.v
elif [ "$1" == "onyx" ]; then
    export WHICH_SOC=onyx
    ref=onyx-4x2.v
    flags="$flags --rv --sparse-cgra --sparse-cgra-combined"

else
    echo "$HELP" && exit 13
fi

echo '--- RTL test BEGIN ($1)' `date`
echo "FLAGS: $flags"


    ########################################################################
    ########################################################################
    ########################################################################

    # FIXME this makes a big mess in top-level dir /aha
    # Why not build in a subdir e.g. tmp-rtl-gold-check? (Would probably break a lot of things.)

    # Prep/clean
    cd /aha
    rm -rf garnet/genesis_verif
    rm -f  garnet/garnet.v

    # Build new rtl
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
test -f $ref && rm $ref

# I guess the most recent cd left us in "/aha/garnet" :(

refdir=../aha/bin/ref
cp $refdir/$ref.gz . || exit 13
gunzip $ref.gz
f1=design.v; f2=$ref

# Need 'sed s/unq...' to handle the case where both designs are
# exactly the same but different "unq" suffixes e.g.
#     < Register_unq3 Register_inst0 (
#     > Register_unq2 Register_inst0 (
#
# Need 's/_O._value_O/...' because generator seems to randomly assign
# the equivalent values 'PE_onyx_inst_onyxpeintf_O3_value_O' and '...O4_value_O' :(

function vcompare {
         cat $1 |
         sed 's/_O._value_O/_Ox_value_O/g' | # Treat all zeroes as equivalent
         sed 's/,$//'           | # No trailing commas
         sed 's/unq[0-9*]/unq/' | # Canonicalize unq's
         sed '/^\s*$/d'         | # No blank lines
         sort                   | # Out-of-order is okay
         cat
}
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

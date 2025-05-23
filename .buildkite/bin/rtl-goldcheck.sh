#!/bin/bash

########################################################################
# TODO want option to run 32x16 run maybe?
# - --4x2 or something maybe
# - or maybe "rtl-gold-check <amber|onyx> <--4x2 | --32x16>"


########################################################################
# --help switch

cmd=$0

HELP="
DESCRIPTION:
  Builds '/aha/garnet/design.v' RTL for a 4x2 amber, onyx or zircon SoC.
  Compares to reference build.

USAGE:
   $cmd amber      # Build and compare amber RTL
   $cmd onyx       # Build and compare onyx RTL
   $cmd zircon     # Build and compare zircon RTL

EXAMPLE
   $cmd amber && echo PASS || echo FAIL

"
[ "$1" == "--help" ] && echo "$HELP" && exit

########################################################################
# Script is designed to work from inside a docker container

if ! test -e aha; then
  echo 'ERROR cannot find root directory "/aha"'
  echo 'Must be inside aha docker container for script to work'
  exit 13
fi

export GARNET_HOME=/aha/garnet
echo "--- Found GARNET_HOME=$GARNET_HOME"

########################################################################
# Assemble the generation command-lie flags, env vars, etc.

width=32; height=$((width/2))  # slow 32x16
width=4;  height=$((width/2))  # quick 4x2
if [ "$1" == "zircon" ]; then
    width=8; height=2  # zircon 8x8
fi
wh="--width $width --height $height"

# FIXME should really use garnet's gen_rtl.sh to generate the RTL and flags etc.
# This would require some kind of --no-docker flag for gen_rtl.sh or some such...

# RTL-build flags (flags are very different b/c divergence of garnet.py, garnet_amber.py
amber_flags="$wh --pipeline_config_interval 8 -v --glb_tile_mem_size 256"
onyx_flags="$wh --verilog --use_sim_sram --glb_tile_mem_size 128"
zircon_flags="$wh --verilog \
--use_sim_sram \
--glb_tile_mem_size 128 \
--using-matrix-unit \
--mu-datawidth 16 \
--give-north-io-sbs \
--num-fabric-cols-removed 4 \
--mu-oc-0 8 \
--include-E64-hw \
--include-multi-bank-hw \
--include-mu-glb-hw \
--use-non-split-fifos \
--exclude-glb-ring-switch"

export WHICH_SOC=$1

# Amber needs a slightly different versions for some of the submodules
# Onyx needs extra gen flags

if [ "$1" == "amber" ]; then
    # Update docker to match necessary amber environment
    $GARNET_HOME/mflowgen/common/rtl/gen_rtl.sh -u | tee tmp-amber-updates.sh
    bash -c 'set -x; source tmp-amber-updates.sh'
    flags="$amber_flags"

elif [ "$1" == "onyx" ]; then
    flags="$onyx_flags"

elif [ "$1" == "zircon" ]; then
    flags="$zircon_flags"

else
    echo "$HELP" && exit 13
fi


########################################################################
echo "--- RTL test BEGIN ($1)" `date`
echo "WHICH_SOC: $WHICH_SOC"
echo "FLAGS: $flags"

# FIXME: this basically duplicates what is done by gen_rtl.sh;
# TODO should build/fix some kind of "build-rtl-only" for
# $GARNET_HOME/mflowgen/common/rtl/gen_rtl.sh and call that instead,
# like we do above for submodule updates.

# Prep/clean
cd /aha
rm -rf garnet/genesis_verif
rm -f  garnet/garnet.v

# Build new rtl
source /aha/bin/activate; # Set up the build environment
aha garnet $flags

cd /aha/garnet  # Everything we built and/or need is in /aha/garnet
if [ "$1" == "amber" ]; then

    # Assemble final design.v
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
else
    cp garnet.v design.v
fi

printf "\n"


########################################################################
echo "+++ Compare result to reference build"
# echo "+++ Compare result to reference build FAIL"

cd /aha/garnet  # This is where design.v lives

# Reference designs are gzipped to save space
ref=${WHICH_SOC}-4x2.v

refdir=/aha/.buildkite/bin/ref
cp $refdir/$ref.gz . || exit 13
test -f $ref && rm $ref  # Just in case there's a stale copy, I guess
gunzip $ref.gz
f1=design.v; f2=$ref

# Use this to test failure mode
# echo '+++ TIME TO FAIL!!!'
# echo foo > foo.deleteme; f1=foo.deleteme

function vcompare { /aha/.buildkite/bin/vcompare.sh $*; }

printf "\n"
echo "Comparing `vcompare $f1 | wc -l` lines of $f1"
echo "versus    `vcompare $f2 | wc -l` lines of $f2"
printf "\n"

echo "diff $f1 $f2"
ndiffs=`vcompare $f1 $f2 | wc -l`

if [ "$ndiffs" != "0" ]; then

    # ------------------------------------------------------------------------
    # TEST FAILED

    printf "Test FAILED with $ndiffs diffs\n"
    printf '(To update gold verilog, see $GARNET_REPO/bin/rtl-goldfetch.sh --help)'
    printf "\n"
    printf "Top 40 diffs:"
    vcompare $f1 $f2 | head -40
    exit 13
fi

echo "Test PASSED"

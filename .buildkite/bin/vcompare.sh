#!/bin/bash

# Compare two garnet.v files to see if they are functionally the same
# (or close enough anyway)

# "vcompare" function abstracts/canonicalizes the verilog for fair compare
# 
# Need 'sed s/unq...' to handle the case where both designs are
# exactly the same but different "unq" suffixes e.g.
#     < Register_unq3 Register_inst0 (
#     > Register_unq2 Register_inst0 (
#
#     < Register     Register_inst0 (
#     > Register_unq Register_inst0 (
#
# Need 's/_O._value_O/...' because generator seems e.g. to randomly assign
# the equivalent values 'PE_onyx_inst_onyxpeintf_O3_value_O' and '...O4_value_O' :(
function vcompare {
    cat $1 |
    sed 's/_O._value_O/_Ox_value_O/g' | # Treat all zeroes as equivalent
    sed 's/,$//'           | # No trailing commas
    sed 's/_unq[0-9*]//'   | # Canonicalize unq's
    sed '/^\s*$/d'         | # No blank lines
    sort                   | # Out-of-order is okay
    cat
}
# Two arguments: apply vcompare filter to both files and diff them
if [ "$2" ]; then
    diff -Bb -I Date <(vcompare $1) <(vcompare $2)
else
    vcompare $1
fi

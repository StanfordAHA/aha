#!/bin/bash

# Where is cmake? E.g. cmdir=/usr/local/lib/python3.8/dist-packages/cmake
python3 -c 'import cmake; print(cmake.__file__)'
cmdir=`python3 -c 'import cmake; print(cmake.__file__)' | sed 's/.__init__.py//'`
cversion=`cmake --version | awk '{print $NF; exit}'`  # Should be "3.28.1" maybe

# Dockerfile copies this script to /aha/pono/contrib/pono-hack/pono-hack.sh
if [ "$1" == '--install' ]; then
    # Replace "official" cmake with this script
    set -x

    # Move old cmake to cmake_orig
    if test -e $cmdir/data/bin/cmake_orig; then
        echo 'Done already did it (cmake_orig exists and I will not write over it)'
        rm $cmdir/data/bin/cmake || echo okay
    else
        mv $cmdir/data/bin/cmake $cmdir/data/bin/cmake_orig
    fi

    # Copy this hack script in place of the "real" cmake
    cp /aha/pono/contrib/pono-hack/pono-hack.sh $cmdir/data/bin/cmake

    # Rewrite init.py to call cmake_orig instead of cmake
    if test -e $cmdir/__init__.py.bku; then
        echo 'Done already did it (cmake_orig exists and I will not write over it)'
        rm $cmdir/__init__.py || echo okay
    else
        cp -p $cmdir/__init__.py $cmdir/__init__.py.bku
    fi
    sed -i "/_program.*'cmake'/s/cmake/cmake_orig/" $cmdir/__init__.py

    # Verify the change:
    #   <  _program('cmake',      *sys.argv[1:])
    #   >  _program('cmake_orig', *sys.argv[1:])
    diff $cmdir/__init__.py.bku $cmdir/__init__.py || echo okay

elif [ "$1" == '--uninstall' ]; then
    # Undo the hack and put cmake back the way it was I hope
    set -x

    echo "pono-hack: pip uninstall hacked cmake"
    yes | python3 -m pip uninstall cmake
    old_cmake=/aha/lib/python3.8/site-packages/cmake
    test -e ${cmdir} && mv ${cmdir} ${cmdir}-orig-deleteme

    echo "pono-hack: pip (re)install cmake==$cversion"
    yes | python3 -m pip install cmake==$cversion
    wait; sleep 10

else
    # Pass args to real cmake, now renamed cmake_orig

    echo "$$ WARNING Using hacked cmake, see /aha/aha/bin/pono-hack"

    echo "xx$@xx" | grep guess-download-Production && echo "$$ pono-hack: subverting config.guess download..."
    echo "xx$@xx" | grep sub-download-Production   && echo "$$ pono-hack: subverting config.sub download..."

    # Looking for this arg pattern:
    # '-P' '/aha/pono/deps/smt-switch/deps/cvc5/build/deps/src/ANTLR3-EP-config.guess-stamp/\
    #            ANTLR3-EP-config.guess-download-Production.cmake'
    # echo "$$ I SEE ARGS"; for a in "$@"; do echo "$$  '$a'"; done; echo ''

    # Dockerfile should have already copied config.{sub,guess} to /aha/pono/contrib/pono-hack/
    src=/aha/pono/contrib/pono-hack
    dst=/aha/pono/deps/smt-switch/deps/cvc5/build/deps/src
    if echo "xx$@xx" | grep guess-download-Production; then
        echo "$$ pono-hack: copy 'config.guess' and exit"
        cp $src/config.guess $dst
        ls -l $src/config.guess $dst/config.guess
    elif echo "xx$@xx" | grep sub-download-Production; then
        echo "$$ pono-hack: copy 'config.sub' and exit"
        cp $src/config.sub $dst
        ls -l $src/config.sub $dst/config.sub
    else
        echo "$$ pono-hack: passing args through to real cmake"
        exec $cmdir/data/bin/cmake_orig "$@"
    fi
fi
exit 0  # Success!

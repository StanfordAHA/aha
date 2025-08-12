#!/bin/bash

# Where is cmake? E.g. cmdir=/usr/local/lib/python3.8/dist-packages/cmake
python3 -c 'import cmake; print(cmake.__file__)'
cmdir=`python3 -c 'import cmake; print(cmake.__file__)' | sed 's/.__init__.py//'`

# Dockerfile copies this script to /aha/pono/contrib/pono-hack/pono-hack.sh
if [ "$1" == '--install' ]; then

    # Replace "official" cmake with this script
    echo FOOOOOOOOOOOOOOOOOOOO

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
    diff $cmdir/__init__.py.bku $cmdir/__init__.py || echo okay

else
    # Pass args to real cmake, now renamed cmake_orig

    python3 -c 'import cmake; print(cmake.__file__)'
    d=`python3 -c 'import cmake; print(cmake.__file__)' | sed 's/.__init__.py//'`

    echo '$$ fooooooo and hello i am fake cmake hahahahaha'

    echo "xx$@xx" | grep guess-download-Production && echo "$$ barrrrrrr guess what"
    echo "xx$@xx" | grep sub-download-Production && echo "$$ barrrrrrr what sub"

    echo "$$ I SEE ARGS"
    for a in "$@"; do echo "$$  '$a'"; done
    echo ''

    # Dockerfile should have already copied config.{sub,guess} to /aha/pono/contrib/pono-hack/
    if echo "xx$@xx" | grep guess-download-Production; then
        echo "$$ barrr copy 'config.guess' and exit"
        src=/aha/pono/contrib/pono-hack
        dst=/aha/pono/deps/smt-switch/deps/cvc5/build/deps/src
        cp $src/config.guess $dst
        ls -l $src/config.guess $dst/config.guess
    elif echo "xx$@xx" | grep sub-download-Production; then
        echo "$$ barrr copy 'config.sub' and exit"
        src=/aha/aha/bin/pono-hack
        dst=/aha/pono/deps/smt-switch/deps/cvc5/build/deps/src
        cp $src/config.sub $dst
        ls -l $src/config.sub $dst/config.sub
    else
        echo 'fooo passing args through to real cmake'
        exec $cmdir/data/bin/cmake_orig "$@"
    fi
fi
exit 0  # Success!

#   <  _program_exit('cmake',      *sys.argv[1:])
#   >  _program_exit('cmake_orig', *sys.argv[1:])


# ls -l /aha/pono/deps/smt-switch/deps/cvc5/build/deps/src/ANTLR3-EP-config.sub-stamp/ANTLR3-EP-config.sub-download-Production.cmake
# /aha/pono/deps/smt-switch/deps/cvc5/build/deps/src/ANTLR3-EP-config.sub-stamp/ANTLR3-EP-config.sub-download*.log
# ls -l /aha/pono/deps/smt-switch/deps/cvc5/build/deps/src/ANTLR3-EP-config.sub-stamp/ANTLR3-EP-config.sub-download*.log
# 
# 
# 3396070 I SEE ARGS
# 3396070  '-P'
# 3396070  '/aha/pono/deps/smt-switch/deps/cvc5/build/deps/src/ANTLR3-EP-config.guess-stamp/ANTLR3-EP-config.guess-download-Production.cmake'

# >>> import cmake; print(cmake.__file__)

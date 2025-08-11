#!/bin/bash

echo FOOOOOOOOOOOOOOOOOOOO
ls -l /usr/local/lib/python3.8/dist-packages/cmake/data/bin/cmake

set -x
python3 -c 'import cmake; print(cmake.__file__)'
d=`python3 -c 'import cmake; print(cmake.__file__)' | sed 's/.__init__.py//'`
echo d=$d

ls -l $d/data/bin
ls -l $d/data/bin/cmake

mv $d/data/bin/cmake $d/data/bin/cmake_orig

cat <<EOF > $d/data/bin/cmake
#!/bin/bash

echo 'fooooooo and hello i am fake cmake hahahahaha'
echo 'I SEE ARGS'
for a in "$@"; do echo "  '$a'"; done
echo ''

echo "xx$@xx" | guess && echo 'barrrrrrr guess what'


echo 'fooo passing args through to real cmake'
exec $d/data/bin/cmake_orig "$@"

EOF


# >>> import cmake; print(cmake.__file__)

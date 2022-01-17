#!/bin/bash

# Download tarball from https://github.com/OpenImageIO/oiio/releases
# and place it in this folder
OIIO_TARBALL=$1
OIIO_ROOT_DIR=${OIIO_TARBALL/.tar.gz/}

# Remove old build root
rm -rf $OIIO_ROOT_DIR

# Unpack tarball
tar vxf $OIIO_TARBALL

OIIO_BUILD_DIR=$OIIO_ROOT_DIR/build
mkdir -p $OIIO_BUILD_DIR

# Enter build dir
cd $OIIO_BUILD_DIR; \
cmake .. \
-DCMAKE_INSTALL_PREFIX=./dist \
-DUSE_PYTHON=1 \
-DUSE_QT=0 \
-DOIIO_BUILD_TESTS=0 \
-DUSE_BUILD_SCRIPTS=1 && \
make -j $(nproc) && make install


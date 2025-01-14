FROM    nvidia/cuda:12.2.0-devel-rockylinux9 AS base


#RUN     dnf -y install s3cmd libgomp httpd24-libcurl icc-profiles-openicc imagemagick python-pip && \
RUN     dnf install epel-release -y && \
        dnf --enablerepo=crb -y install xorg-x11-util-macros libgomp python3-pip ninja-build ImageMagick s3cmd yaml-cpp \
                python3-devel clang git-clang-format libtiff libtiff-devel bzip2 bzip2-devel bzip2-libs tbb tbb-devel libwebp giflib patch vim && \
        dnf clean all;

RUN pip install six testresources recommonmark sphinx-press-theme sphinx-tabs breathe pyseq  pillow PyYAML meson kaleido plotly pandas jinja2 OpenTimelineIO
RUN pip install awscli

FROM        base AS build

WORKDIR     /tmp/workdir

ENV         FFMPEG_VERSION=7.1 \
    AOM_VERSION=v3.10.0 \
    CHROMAPRINT_VERSION=1.5.0 \
    FDKAAC_VERSION=0.1.5 \
    FONTCONFIG_VERSION=2.12.4 \
    FREETYPE_VERSION=2.13.3 \
    FRIBIDI_VERSION=0.19.7 \
    KVAZAAR_VERSION=2.0.0 \
    LAME_VERSION=3.100 \
    LIBASS_VERSION=0.13.7 \
    LIBPTHREAD_STUBS_VERSION=0.4 \
    LIBVIDSTAB_VERSION=1.1.0 \
    LIBXCB_VERSION=1.15 \
    XCBPROTO_VERSION=1.15 \
    OGG_VERSION=1.3.2 \
    OPENCOREAMR_VERSION=0.1.5 \
    OPUS_VERSION=1.5.2 \
    OPENJPEG_VERSION=2.5.2 \
    THEORA_VERSION=1.1.1 \
    VORBIS_VERSION=1.3.5 \
    VPX_VERSION=1.8.0 \
    WEBP_VERSION=1.4.0 \
    X264_VERSION=20191217-2245-stable \
    X265_VERSION=3.6 \
    XAU_VERSION=1.0.9 \
    XORG_MACROS_VERSION=1.19.2 \
    XPROTO_VERSION=7.0.31 \
    XVID_VERSION=1.3.7 \
    LIBSVT_AV1_VERSION=2.2.1 \
    LIBXML2_VERSION=2.9.12 \
    LIBBLURAY_VERSION=1.3.4 \
    LIBZMQ_VERSION=4.3.5 \
    LIBSRT_VERSION=1.5.3 \
    LIBARIBB24_VERSION=1.0.3 \
    LIBPNG_VERSION=1.6.9 \
    LIBVMAF_VERSION=3.0.0 \
    LIBZIMG_VERSION=3.0.5 \ 
    VMAF_MODEL_DIR=/usr/share/vmaf/model \
    SRC=/usr/local

# OCIO and OIIO
ENV         LD_LIBRARY_PATH=/usr/local/lib64:/usr/local/lib:/opt/rh/httpd24/root/usr/lib64/ \
            OCIO=ocio://studio-config-v1.0.0_aces-v1.3_ocio-v2.1 \
            VMAF_MODEL_DIR=${VMAF_MODEL_DIR} \
            ASWF_OIIO_VERSION=2.5.16.0 \
            ASWF_OCIO_VERSION=2.2.1 \
            ASWF_BOOST_VERSION=1.82.0 \
            ASWF_PYTHON_MAJOR_MINOR_VERSION=3.11 \
            ASWF_OPENEXR_VERSION=3.2.4

ARG         FREETYPE_SHA256SUM="5eab795ebb23ac77001cfb68b7d4d50b5d6c7469247b0b01b2c953269f658dac freetype-2.10.4.tar.gz"
ARG         FRIBIDI_SHA256SUM="3fc96fa9473bd31dcb5500bdf1aa78b337ba13eb8c301e7c28923fea982453a8 0.19.7.tar.gz"
ARG         LIBASS_SHA256SUM="8fadf294bf701300d4605e6f1d92929304187fca4b8d8a47889315526adbafd7 0.13.7.tar.gz"
ARG         LIBVIDSTAB_SHA256SUM="14d2a053e56edad4f397be0cb3ef8eb1ec3150404ce99a426c4eb641861dc0bb v1.1.0.tar.gz"
ARG         OGG_SHA256SUM="e19ee34711d7af328cb26287f4137e70630e7261b17cbe3cd41011d73a654692 libogg-1.3.2.tar.gz"
ARG         OPUS_SHA256SUM="65c1d2f78b9f2fb20082c38cbe47c951ad5839345876e46941612ee87f9a7ce1 opus-1.5.2.tar.gz"
ARG         THEORA_SHA256SUM="40952956c47811928d1e7922cda3bc1f427eb75680c3c37249c91e949054916b libtheora-1.1.1.tar.gz"
ARG         VORBIS_SHA256SUM="6efbcecdd3e5dfbf090341b485da9d176eb250d893e3eb378c428a2db38301ce libvorbis-1.3.5.tar.gz"
# ARG         XVID_SHA256SUM="aeeaae952d4db395249839a3bd03841d6844843f5a4f84c271ff88f7aa1acff7 xvidcore-1.3.7.tar.gz"
ARG         LIBBLURAY_SHA256SUM="a3dd452239b100dc9da0d01b30e1692693e2a332a7d29917bf84bb10ea7c0b42 libbluray-1.1.2.tar.bz2"
ARG         LIBZMQ_SHA256SUM="02ecc88466ae38cf2c8d79f09cfd2675ba299a439680b64ade733e26a349edeb v4.3.2.tar.gz"
ARG         LIBARIBB24_SHA256SUM="f61560738926e57f9173510389634d8c06cabedfa857db4b28fb7704707ff128 v1.0.3.tar.gz"


#ARG         LD_LIBRARY_PATH=/opt/ffmpeg/lib
ARG         MAKEFLAGS="-j2"
#ARG         PKG_CONFIG_PATH="/opt/ffmpeg/share/pkgconfig:/opt/ffmpeg/lib/pkgconfig:/opt/ffmpeg/lib64/pkgconfig"
ARG         PKG_CONFIG_PATH="/usr/local/share/pkgconfig:/usr/local/lib/pkgconfig:/usr/local/lib64/pkgconfig"
ARG         PREFIX=/usr/local
#ARG         LD_LIBRARY_PATH="/opt/ffmpeg/lib:/opt/ffmpeg/lib64"
ARG         LD_LIBRARY_PATH="/usr/local/lib:/usr/local/lib64"


RUN     buildDeps="autoconf \
                   automake \
		   cmake \
                   bzip2 \
                   diffutils \
                   expat-devel \
                   file \
                   gcc \
                   gcc-c++ \
                   git \
                   gperf \
                   libtool \
                   make \
                   perl \
                   python3 \
                   openssl-devel \
                   tar \
                   yasm \
                   which \
                   zlib-devel" && \
        echo "${SRC}/lib" > /etc/ld.so.conf.d/libc.conf && \
        yum --enablerepo=extras install -y epel-release && \
        yum --enablerepo=epel install -y ${buildDeps} 


RUN     #alternatives --install /usr/bin/cmake cmake /usr/bin/cmake3 0 && \
        # Install the tools required to build nasm 2.14.02 \
        nasmDeps="asciidoc \
                  perl-Font-TTF \
                  perl-Sort-Versions \
                  xmlto"  \
        yum --enablerepo=epel install -y ${nasmDeps} 

        # Compile and install nasm 2.14.02 \
RUN        DIR=/tmp/nasm && \
        mkdir -p ${DIR} && \
        curl -LSs https://www.nasm.us/pub/nasm/releasebuilds/2.14.02/nasm-2.14.02.tar.gz | \
        tar xzC ${DIR} --strip-components=1 && \
        pushd ${DIR} && \
        ./configure --host=x86_64-redhat-linux-gnu \
                    --build=x86_64-redhat-linux-gnu \
                    --prefix=/usr/local \
                    --exec-prefix=/usr/local \
                    --bindir=/usr/local/bin \
                    --sbindir=/usr/local/sbin \
                    --sysconfdir=/usr/local/etc \
                    --datadir=/usr/local/share \
                    --includedir=/usr/local/include \
                    --libdir=/usr/local/lib \
                    --libexecdir=/usr/local/libexec \
                    --enable-sections && \
        make all && \
        make install && \
        make install_rdf && \
        popd && rm -rf ${DIR} && \
        alternatives --install /usr/bin/nasm nasm /usr/local/bin/nasm 0 
        # Now that we have a modern nasm build and available, we can undo the last \
        # yum transaction as none of those packages are required for the rest of the build \
        #yum history undo $(yum history info | grep 'Transaction ID' | awk -F: '{print$2}' | tr -d ' ') -y && \
        #yum autoremove -y

## libvmaf https://github.com/Netflix/vmaf
RUN \
        if which meson || false; then \
        echo "Building VMAF." && \
        DIR=/tmp/vmaf && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://github.com/Netflix/vmaf/archive/v${LIBVMAF_VERSION}.tar.gz && \
        tar -xz --strip-components=1 -f v${LIBVMAF_VERSION}.tar.gz && \
        cd /tmp/vmaf/libvmaf && \
        meson build --buildtype release --prefix=${PREFIX} && \
        ninja -vC build && \
        ninja -vC build install && \
        mkdir -p ${PREFIX}/share/model/ && \
        cp -r ${DIR}/model/* ${PREFIX}/share/model/ && \
        mkdir -p ${VMAF_MODEL_DIR} && \
	echo "Creating VMAF DIRECTORY:" ${VMAF_MODEL_DIR} && \
        cp -vr ${DIR}/model/* ${VMAF_MODEL_DIR} && \
        rm -rf ${DIR}; \
        else \
        echo "VMAF skipped."; \
        fi

## opencore-amr https://sourceforge.net/projects/opencore-amr/
RUN \
        DIR=/tmp/opencore-amr && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sL https://sourceforge.net/projects/opencore-amr/files/opencore-amr/opencore-amr-${OPENCOREAMR_VERSION}.tar.gz/download | \
        tar -zx --strip-components=1 && \
        ./configure --prefix="${PREFIX}" --enable-shared  && \
        make && \
        make install && \
        rm -rf ${DIR}
## x264 http://www.videolan.org/developers/x264.html

RUN \
        DIR=/tmp/x264 && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sL https://download.videolan.org/pub/videolan/x264/snapshots/x264-snapshot-${X264_VERSION}.tar.bz2 | \
        tar -jx --strip-components=1 && \
        ./configure --prefix="${PREFIX}" --enable-shared --enable-pic --disable-cli --bit-depth=10 && \
        make && \
        make install && \
        rm -rf ${DIR}

### x265 http://x265.org/


RUN \
        DIR=/tmp/x265 && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sL https://bitbucket.org/multicoreware/x265_git/downloads/x265_${X265_VERSION}.tar.gz | \
        tar -zx --strip-components=1 && \
        cd build/linux && \
        #sed -i "/-DEXTRA_LIB/ s/$/ -DCMAKE_INSTALL_PREFIX=\${PREFIX}/" multilib.sh && \
        #sed -i "/^cmake/ s/$/ -DENABLE_CLI=OFF/" multilib.sh && \
        #./multilib.sh && \
        #make -C 8bit install && \
        #./make-Makefiles.bash && \
        cmake -G "Unix Makefiles" -DHIGH_BIT_DEPTH=ON -DENABLE_CLI=OFF -DMAIN12=ON -DCMAKE_INSTALL_PREFIX="${PREFIX}" ../../source && \
        make  && \
         make install && \
        rm -rf ${DIR}

### libogg https://www.xiph.org/ogg/
RUN \
        DIR=/tmp/ogg && \
        mkdir -p ${DIR} && echo hi && \
        cd ${DIR} && \
        curl -sLO http://downloads.xiph.org/releases/ogg/libogg-${OGG_VERSION}.tar.gz && \
        echo ${OGG_SHA256SUM} | sha256sum --check && \
        tar -zx --strip-components=1 -f libogg-${OGG_VERSION}.tar.gz && \
        ./configure --prefix="${PREFIX}" --enable-shared  && \
        make && \
        make install # && \
        rm -rf ${DIR}

### libopus https://www.opus-codec.org/
RUN \
        DIR=/tmp/opus && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://ftp.osuosl.org/pub/xiph/releases/opus/opus-${OPUS_VERSION}.tar.gz && \
        echo ${OPUS_SHA256SUM} | sha256sum --check && \
        tar -zx --strip-components=1 -f opus-${OPUS_VERSION}.tar.gz && \
        autoreconf -fiv && \
        ./configure --prefix="${PREFIX}" --enable-shared && \
        make && \
        make install && \
        rm -rf ${DIR}

### libvorbis https://xiph.org/vorbis/
RUN \
        DIR=/tmp/vorbis && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO http://downloads.xiph.org/releases/vorbis/libvorbis-${VORBIS_VERSION}.tar.gz && \
        echo ${VORBIS_SHA256SUM} | sha256sum --check && \
        tar -zx --strip-components=1 -f libvorbis-${VORBIS_VERSION}.tar.gz && \
        ./configure --prefix="${PREFIX}" --with-ogg="${PREFIX}" --enable-shared && \
        make && \
        make install && \
        rm -rf ${DIR}

### libtheora http://www.theora.org/
RUN \
        DIR=/tmp/theora && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO http://downloads.xiph.org/releases/theora/libtheora-${THEORA_VERSION}.tar.gz && \
        echo ${THEORA_SHA256SUM} | sha256sum --check && \
        tar -zx --strip-components=1 -f libtheora-${THEORA_VERSION}.tar.gz && \
        ./configure --prefix="${PREFIX}" --with-ogg="${PREFIX}" --enable-shared && \
        make && \
        make install && \
        rm -rf ${DIR}

### libvpx https://www.webmproject.org/code/
RUN \
        DIR=/tmp/vpx && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sL https://codeload.github.com/webmproject/libvpx/tar.gz/v${VPX_VERSION} | \
        tar -zx --strip-components=1 && \
        ./configure --prefix="${PREFIX}" --enable-vp8 --enable-vp9 --enable-vp9-highbitdepth --enable-pic --enable-shared \
        --disable-debug --disable-examples --disable-docs --disable-install-bins  && \
        make && \
        make install && \
        rm -rf ${DIR}

### libwebp https://developers.google.com/speed/webp/
RUN \
        DIR=/tmp/vebp && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sL https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-${WEBP_VERSION}.tar.gz | \
        tar -zx --strip-components=1 && \
        ./configure --prefix="${PREFIX}" --enable-shared  && \
        make && \
        make install && \
        rm -rf ${DIR}

### libmp3lame http://lame.sourceforge.net/
RUN \
        DIR=/tmp/lame && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sL https://sourceforge.net/projects/lame/files/lame/${LAME_VERSION}/lame-${LAME_VERSION}.tar.gz/download | \
        tar -zx --strip-components=1 && \
        ./configure --prefix="${PREFIX}" --bindir="${PREFIX}/bin" --enable-shared --enable-nasm --disable-frontend && \
        make && \
        make install && \
        rm -rf ${DIR}

### xvid https://www.xvid.com/
# RUN \
#         DIR=/tmp/xvid && \
#         mkdir -p ${DIR} && \
#         cd ${DIR} && \
#         curl -sLO http://downloads.xvid.org/downloads/xvidcore-${XVID_VERSION}.tar.gz && \
#         echo ${XVID_SHA256SUM} | sha256sum --check && \
#         tar -zx -f xvidcore-${XVID_VERSION}.tar.gz && \
#         cd xvidcore/build/generic && \
#         ./configure --prefix="${PREFIX}" --bindir="${PREFIX}/bin" && \
#         make && \
#         make install && \
#         rm -rf ${DIR}

### fdk-aac https://github.com/mstorsjo/fdk-aac
RUN \
        DIR=/tmp/fdk-aac && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sL https://github.com/mstorsjo/fdk-aac/archive/v${FDKAAC_VERSION}.tar.gz | \
        tar -zx --strip-components=1 && \
        autoreconf -fiv && \
        ./configure --prefix="${PREFIX}" --enable-shared --datadir="${DIR}" && \
        make && \
        make install && \
        rm -rf ${DIR}

## openjpeg https://github.com/uclouvain/openjpeg
RUN \
        DIR=/tmp/openjpeg && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sL https://github.com/uclouvain/openjpeg/archive/v${OPENJPEG_VERSION}.tar.gz | \
        tar -zx --strip-components=1 && \
        cmake -DBUILD_THIRDPARTY:BOOL=ON -DCMAKE_INSTALL_PREFIX="${PREFIX}" . && \
        make && \
        make install && \
        rm -rf ${DIR}

## freetype https://www.freetype.org/
RUN  \
        DIR=/tmp/freetype && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://download.savannah.gnu.org/releases/freetype/freetype-${FREETYPE_VERSION}.tar.gz && \
        # echo ${FREETYPE_SHA256SUM} | sha256sum --check && \
        tar -zx --strip-components=1 -f freetype-${FREETYPE_VERSION}.tar.gz && \
        ./configure --prefix="${PREFIX}" --disable-static --enable-shared && \
        make && \
        make install && \
        rm -rf ${DIR}

## libvstab https://github.com/georgmartius/vid.stab
RUN  \
        DIR=/tmp/vid.stab && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://github.com/georgmartius/vid.stab/archive/v${LIBVIDSTAB_VERSION}.tar.gz && \
        echo ${LIBVIDSTAB_SHA256SUM} | sha256sum --check &&  \
        tar -zx --strip-components=1 -f v${LIBVIDSTAB_VERSION}.tar.gz && \
        cmake -DCMAKE_INSTALL_PREFIX="${PREFIX}" . && \
        make && \
        make install && \
        rm -rf ${DIR}

## fridibi https://www.fribidi.org/
RUN  \
        DIR=/tmp/fribidi && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://github.com/fribidi/fribidi/archive/${FRIBIDI_VERSION}.tar.gz && \
        echo ${FRIBIDI_SHA256SUM} | sha256sum --check && \
        tar -zx --strip-components=1 -f ${FRIBIDI_VERSION}.tar.gz && \
        sed -i 's/^SUBDIRS =.*/SUBDIRS=gen.tab charset lib bin/' Makefile.am && \
        ./bootstrap --no-config --auto && \
        ./configure --prefix="${PREFIX}" --disable-static --enable-shared && \
        make -j1 && \
        make install && \
        rm -rf ${DIR}

## fontconfig https://www.freedesktop.org/wiki/Software/fontconfig/
RUN  \
        DIR=/tmp/fontconfig && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://www.freedesktop.org/software/fontconfig/release/fontconfig-${FONTCONFIG_VERSION}.tar.bz2 && \
        tar -jx --strip-components=1 -f fontconfig-${FONTCONFIG_VERSION}.tar.bz2 && \
        ./configure --prefix="${PREFIX}" --disable-static --enable-shared && \
        make && \
        make install && \
        rm -rf ${DIR}

## libass https://github.com/libass/libass
RUN  \
        DIR=/tmp/libass && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://github.com/libass/libass/archive/${LIBASS_VERSION}.tar.gz && \
        # echo ${LIBASS_SHA256SUM} | sha256sum --check && \
        tar -zx --strip-components=1 -f ${LIBASS_VERSION}.tar.gz && \
        ./autogen.sh && \
        ./configure --prefix="${PREFIX}" --disable-static --enable-shared && \
        make && \
        make install && \
        rm -rf ${DIR}

## kvazaar https://github.com/ultravideo/kvazaar
RUN \
        DIR=/tmp/kvazaar && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://github.com/ultravideo/kvazaar/archive/v${KVAZAAR_VERSION}.tar.gz && \
        tar -zx --strip-components=1 -f v${KVAZAAR_VERSION}.tar.gz && \
        ./autogen.sh && \
        ./configure --prefix="${PREFIX}" --disable-static --enable-shared && \
        make && \
        make install && \
        rm -rf ${DIR}

RUN \
        DIR=/tmp/aom && \
        git clone --branch ${AOM_VERSION} --depth 1 https://aomedia.googlesource.com/aom ${DIR} ; \
        cd ${DIR} ; \
        rm -rf CMakeCache.txt CMakeFiles ; \
        mkdir -p ./aom_build ; \
        cd ./aom_build ; \
        cmake -DCMAKE_INSTALL_PREFIX="${PREFIX}" -DBUILD_SHARED_LIBS=1 ..; \
        make ; \
        make install ; \
        rm -rf ${DIR}

## zimg https://github.com/sekrit-twc/zimg
RUN  \
        DIR=/tmp/zlib && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://github.com/sekrit-twc/zimg/archive/refs/tags/release-${LIBZIMG_VERSION}.tar.gz && \
        # echo ${LIBASS_SHA256SUM} | sha256sum --check && \
        tar -zx --strip-components=1 -f release-${LIBZIMG_VERSION}.tar.gz && \
        ./autogen.sh && \
        ./configure --prefix="${PREFIX}" --disable-static --enable-shared && \
        make && \
        make install && \
        rm -rf ${DIR}

## libxcb (and supporting libraries) for screen capture https://xcb.freedesktop.org/
RUN \
        DIR=/tmp/xorg-macros && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://www.x.org/archive//individual/util/util-macros-${XORG_MACROS_VERSION}.tar.gz && \
        tar -zx --strip-components=1 -f util-macros-${XORG_MACROS_VERSION}.tar.gz && \
        ./configure --srcdir=${DIR} --prefix="${PREFIX}" && \
        make && \
        make install && \
        rm -rf ${DIR}

RUN \
        DIR=/tmp/xproto && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://www.x.org/archive/individual/proto/xproto-${XPROTO_VERSION}.tar.gz && \
        tar -zx --strip-components=1 -f xproto-${XPROTO_VERSION}.tar.gz && \
        ./configure --srcdir=${DIR} --prefix="${PREFIX}" && \
        make && \
        make install && \
        rm -rf ${DIR}

RUN \
        DIR=/tmp/libXau && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://www.x.org/archive/individual/lib/libXau-${XAU_VERSION}.tar.gz && \
        tar -zx --strip-components=1 -f libXau-${XAU_VERSION}.tar.gz && \
        ./configure --srcdir=${DIR} --prefix="${PREFIX}" && \
        make && \
        make install && \
        rm -rf ${DIR}

RUN \
        DIR=/tmp/libpthread-stubs && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://xcb.freedesktop.org/dist/libpthread-stubs-${LIBPTHREAD_STUBS_VERSION}.tar.gz && \
        tar -zx --strip-components=1 -f libpthread-stubs-${LIBPTHREAD_STUBS_VERSION}.tar.gz && \
        ./configure --prefix="${PREFIX}" && \
        make && \
        make install && \
        rm -rf ${DIR}

RUN \
        DIR=/tmp/libxcb-proto && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://xcb.freedesktop.org/dist/xcb-proto-${XCBPROTO_VERSION}.tar.gz && \
        tar -zx --strip-components=1 -f xcb-proto-${XCBPROTO_VERSION}.tar.gz && \
        ACLOCAL_PATH="${PREFIX}/share/aclocal" ./autogen.sh && \
        ./configure --prefix="${PREFIX}" && \
        make && \
        make install && \
        rm -rf ${DIR}

RUN \
        DIR=/tmp/libxcb && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://xcb.freedesktop.org/dist/libxcb-${LIBXCB_VERSION}.tar.gz && \
        tar -zx --strip-components=1 -f libxcb-${LIBXCB_VERSION}.tar.gz && \
        ACLOCAL_PATH="${PREFIX}/share/aclocal" ./autogen.sh && \
        ./configure --prefix="${PREFIX}" --disable-static --enable-shared && \
        make && \
        make install && \
        rm -rf ${DIR}


## libxml2 - for libbluray
RUN \
        DIR=/tmp/libxml2 && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sL https://github.com/GNOME/libxml2/archive/refs/tags/v${LIBXML2_VERSION}.tar.gz | \
        tar -xz --strip-components=1 && \
        ./autogen.sh --prefix="${PREFIX}" --with-ftp=no --with-http=no --with-python=no && \
        make && \
        make install && \
        rm -rf ${DIR}

## libbluray - Requires libxml, freetype, and fontconfig
RUN \
        DIR=/tmp/libbluray && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://download.videolan.org/pub/videolan/libbluray/${LIBBLURAY_VERSION}/libbluray-${LIBBLURAY_VERSION}.tar.bz2 && \
        # echo ${LIBBLURAY_SHA256SUM} | sha256sum --check && \
        tar -jx --strip-components=1 -f libbluray-${LIBBLURAY_VERSION}.tar.bz2 && \
        ./configure --prefix="${PREFIX}" --disable-examples --disable-bdjava-jar --disable-static --enable-shared && \
        make && \
        make install && \
        rm -rf ${DIR}

## libzmq https://github.com/zeromq/libzmq/
RUN \
        DIR=/tmp/libzmq && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://github.com/zeromq/libzmq/archive/v${LIBZMQ_VERSION}.tar.gz && \
        # echo ${LIBZMQ_SHA256SUM} | sha256sum --check && \
        tar -xz --strip-components=1 -f v${LIBZMQ_VERSION}.tar.gz && \
        ./autogen.sh && \
        ./configure --prefix="${PREFIX}" && \
        make && \
        make check && \
        make install && \
        rm -rf ${DIR}

## libsrt https://github.com/Haivision/srt
RUN \
        DIR=/tmp/srt && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://github.com/Haivision/srt/archive/v${LIBSRT_VERSION}.tar.gz && \
        tar -xz --strip-components=1 -f v${LIBSRT_VERSION}.tar.gz && \
        cmake -DCMAKE_INSTALL_PREFIX="${PREFIX}" . && \
        make && \
        make install && \
        rm -rf ${DIR}

## libpng
RUN \
        DIR=/tmp/png && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        git clone https://git.code.sf.net/p/libpng/code ${DIR} -b v${LIBPNG_VERSION} --depth 1 && \
        ./autogen.sh && \
        ./configure --prefix="${PREFIX}" && \
        make check && \
        make install && \
        rm -rf ${DIR}

## libaribb24
RUN \
        DIR=/tmp/b24 && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        curl -sLO https://github.com/nkoriyama/aribb24/archive/v${LIBARIBB24_VERSION}.tar.gz && \
        # echo ${LIBARIBB24_SHA256SUM} | sha256sum --check && \
        tar -xz --strip-components=1 -f v${LIBARIBB24_VERSION}.tar.gz && \
        autoreconf -fiv && \
        ./configure CFLAGS="-I${PREFIX}/include -fPIC" --prefix="${PREFIX}" && \
        make && \
        make install && \
        rm -rf ${DIR}

 RUN  \
        DIR=/opt/openexr && mkdir -p ${DIR} && cd ${DIR} && \
        curl -sLO "https://github.com/AcademySoftwareFoundation/openexr/archive/refs/tags/v${ASWF_OPENEXR_VERSION}.tar.gz" && \
        # echo ${LIBARIBB24_SHA256SUM} | sha256sum --check && \
        tar -xz --strip-components=1 -f v${ASWF_OPENEXR_VERSION}.tar.gz && \
        mkdir build && \
        cd build && \
        cmake \
                -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
                -DOPENEXR_BUILD_PYTHON_LIBS="on" \
                .. && \
        make && \
        make install

 RUN \
         DIR=/tmp/svtav1 && \
         mkdir -p ${DIR} && \
         cd ${DIR} && \
         curl -sLO https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v1.8.0/SVT-AV1-v${LIB_SVT_AV1_VERSION}.tar.gz && \
         tar -xz --strip-components=1 -f SVT-AV1-v${LIB_SVT_AV1_VERSION}.tar.gz && \
         cd Build && \
         cmake .. -G"Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="${PREFIX}"  && \
         make && \
         make install && \
         rm -rf ${DIR}

run \
        DIR=/tmp/nvcodec && \
        mkdir -p ${DIR} && \
        cd ${DIR} && \
        git clone https://git.videolan.org/git/ffmpeg/nv-codec-headers.git && \
        cd nv-codec-headers && make install

# ## Download ffmpeg https://ffmpeg.org/
RUN  \
        DIR=/tmp/ffmpeg && mkdir -p ${DIR} && cd ${DIR} && \
        curl -sLO https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.bz2 && \
        tar -jx --strip-components=1 -f ffmpeg-${FFMPEG_VERSION}.tar.bz2 

## Build ffmpeg https://ffmpeg.org/
RUN  \
        DIR=/tmp/ffmpeg && cd ${DIR} && \
        ./configure \
        --disable-debug \
        --disable-doc \
        # --enable-cuda-nvcc \
        --enable-libnpp \
        --disable-ffplay \
        --enable-fontconfig \
        --enable-cuda-nvcc \
        --enable-gpl \
        --enable-libaom \
        --enable-libsvtav1 \
        --enable-libaribb24 \
        --enable-libass \
        --enable-libbluray \
        --enable-libfdk_aac \
        --enable-libfreetype \
        --enable-libkvazaar \
        --enable-libmp3lame \
        --enable-libopencore-amrnb \
        --enable-libopencore-amrwb \
        --enable-libopenjpeg \
        # --enable-libopus \
        --enable-libsrt \
        --enable-libvmaf \
        --enable-libtheora \
        --enable-libvidstab \
        --enable-libvorbis \
        --enable-libvpx \
        --enable-libwebp \
        --enable-libx264 \
        --enable-libx265 \
        # --enable-libxcb \
        # --enable-libxvid \
        --enable-libzmq \
        --enable-nonfree \
        --enable-openssl \
        --enable-postproc \
        --enable-shared \
        --enable-small \
        --enable-version3 \
        --enable-libzimg \
        --extra-cflags="-I${PREFIX}/include -I/usr/local/cuda/include" \
        --extra-ldflags="-L${PREFIX}/lib -L/usr/local/cuda/lib64" \
        --extra-libs=-ldl \
        --extra-libs=-lpthread \
        --prefix="${PREFIX}" && \
        make clean && \
        make -j 8 && \
        make install && \
        make tools/zmqsend && cp tools/zmqsend ${PREFIX}/bin/ && \
        make distclean && \
        hash -r && \
        cd tools && \
        make qt-faststart && cp qt-faststart ${PREFIX}/bin/

RUN DIR=/tmp/boost  && mkdir -p ${DIR} && cd ${DIR} && \
        BOOST_MAJOR_MINOR=$(echo "${ASWF_BOOST_VERSION}" | cut -d. -f-2) && \
        BOOST_MAJOR=$(echo "${ASWF_BOOST_VERSION}" | cut -d. -f-1) && \
        BOOST_MINOR=$(echo "${BOOST_MAJOR_MINOR}" | cut -d. -f2-) && \
        BOOST_PATCH=$(echo "${ASWF_BOOST_VERSION}" | cut -d. -f3-) && \
        BOOST_VERSION_U="${BOOST_MAJOR}_${BOOST_MINOR}_${BOOST_PATCH}" && \
        curl --location "https://sourceforge.net/projects/boost/files/boost/${ASWF_BOOST_VERSION}/boost_${BOOST_VERSION_U}.tar.gz" -o boost_${BOOST_VERSION_U}.tar.gz && \
        tar -xz --strip-components=1 -f boost_${BOOST_VERSION_U}.tar.gz && \
        sh bootstrap.sh --with-python=${ASWF_INSTALL_PREFIX}/bin/python${ASWF_PYTHON_MAJOR_MINOR_VERSION} --with-python-version=${ASWF_PYTHON_MAJOR_MINOR_VERSION} --with-python-root=${PREFIX}/lib/python${ASWF_PYTHON_MAJOR_MINOR_VERSION} && \
        ./b2 install -j2 variant=release toolset=gcc link=shared \
        --with-atomic \
        --with-chrono \
        --with-container \
        --with-context \
        --with-coroutine \
        --with-date_time \
        --with-exception \
        --with-filesystem \
        --with-graph \
        --with-graph_parallel \
        --with-iostreams \
        --with-locale \
        --with-log \
        --with-math \
        --with-mpi \
        --with-program_options \
        --with-random \
        --with-regex \
        --with-serialization \
        --with-system \
        --with-test \
        --with-thread \
        --with-timer \
        --with-type_erasure \
        --with-wave \
        --prefix="${PREFIX}" \
        --with-python \
        cxxstd=14 && \
        rm -rf ${DIR}


RUN  \
        DIR=/opt/ocio && mkdir -p ${DIR} && cd ${DIR} && \
        curl -sLO https://github.com/AcademySoftwareFoundation/OpenColorIO/archive/v${ASWF_OCIO_VERSION}.tar.gz && \
        tar -xz --strip-components=1 -f v${ASWF_OCIO_VERSION}.tar.gz && \
        mkdir build && \
        cd build && \
        cmake \
    -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
    -DOCIO_BUILD_STATIC=OFF \
    -DOCIO_BUILD_TRUELIGHT=OFF \
    -DOCIO_BUILD_APPS=OFF \
    -DOCIO_BUILD_NUKE=OFF -DPython_EXECUTABLE=`which python3` \
    -DOCIO_INSTALL_EXT_PACKAGES=MISSING \
    -DCMAKE_CXX_FLAGS="-Wno-error=unused-function -Wno-error=deprecated-declarations"\
    .. && \
        make  && \
        make install && \
        rm -rf ${DIR}

# RUN \
#         DIR=/tmp/libsquish && mkdir -p ${DIR} && cd ${DIR} && \
#         curl -sL https://sourceforge.net/projects/libsquish/files/libsquish-1.15.tgz/download | \
#         tar zx && \
#         cmake . && \
#         make install

## Download and install OIIO again. Currently the VFXALL version of oiiotool does not have ocio compiled
# into it, we hope a future version will have that fixed.

RUN  \
        DIR=/opt/oiio && mkdir -p ${DIR} && cd ${DIR} && \
        curl -sLO https://github.com/OpenImageIO/oiio/archive/refs/tags/v${ASWF_OIIO_VERSION}.tar.gz && \
        # echo ${LIBARIBB24_SHA256SUM} | sha256sum --check && \
        tar -xz --strip-components=1 -f v${ASWF_OIIO_VERSION}.tar.gz && \
        src/build-scripts/build_pybind11.bash && \
        #src/build-scripts/build_OpenJPEG.bash && \
        src/build-scripts/build_libjpeg-turbo.bash && \
        src/build-scripts/build_Ptex.bash && \
        cp -rp ext/dist/* /usr/local && \
        #src/build-scripts/build_gif.bash  && \
        make -j 4 INSTALL_PREFIX=/usr/local OIIO_BUILD_TESTS=0 USE_QT=0 USE_NUKE=0 ENABLE_Libsquish=0 ENABLE_OpenGL=0 \
                ENABLE_OpenCV=0 ENABLE_QT5=0 ENABLE_OpenVDB=0 ENABLE_LibRaw=0 \
                ENABLE_Libheif=0 ENABLE_FFmpeg=0 install

WORKDIR     /test


# ENV         LD_LIBRARY_PATH=/usr/local/lib64:/usr/local/lib

# #ENTRYPOINT  ["ffmpeg"]

# COPY --from=build /usr/local/ /usr/local/

# # Let's make sure the app built correctly
# # Convenient to verify on https://hub.docker.com/r/jrottenberg/ffmpeg/builds/ console output

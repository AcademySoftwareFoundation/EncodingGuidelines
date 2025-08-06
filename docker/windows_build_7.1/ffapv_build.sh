
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig
./configure    --extra-ldflags=-L/usr/local/lib/oapv/import    --extra-libs="-lpthread -lm"   --disable-debug         --disable-doc             --enable-ffplay                --enable-gpl         --enable-libaom         --enable-libsvtav1          --enable-libfdk_aac         --enable-libmp3lame        --enable-libopenjpeg      --enable-libvmaf         --enable-libtheora            --enable-libvorbis         --enable-libvpx         --enable-libwebp         --enable-libx264    --enable-liboapv     --enable-libx265        --enable-nonfree         --enable-openssl         --enable-postproc         --enable-shared         --enable-small         --enable-version3         --enable-libzimg              --extra-libs=-lpthread         --prefix="${PREFIX}" 
  #     --enable-libfreetype       --enable-fontconfig   --enable-cuda-nvcc         --extra-cflags="-I${PREFIX}/include -I/usr/local/cuda/include"         --extra-ldflags="-L${PREFIX}/lib -L/usr/local/cuda/lib64"   --extra-libs=-ldl     
make clean 
make -j $(nproc)
make install 

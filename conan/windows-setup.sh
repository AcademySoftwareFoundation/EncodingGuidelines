pacman -S --noconfirm mingw-w64-x86_64-gdb mingw-w64-x86_64-make
pacman -S --noconfirm mingw-w64-x86_64-python-pip mingw-w64-x86_64-ninja
pacman -S --noconfirm mingw-w64-x86_64-nasm mingw-w64-x86_64-yasm
pacman -S --noconfirm base-devel
pacman -S --needed mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake
export CONAN_HOME="/c/.c2"

pip install conan
cd recipes/ffmpeg/all
conan export . --name ffmpeg --version 8.1
cd ../../opencolorio/all
conan export . --name opencolorio --version 2.5.1
cd ../../libvmaf/all
conan export . --name libvmaf --version 3.0.0
cd ../../..
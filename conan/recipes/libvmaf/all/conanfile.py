import os
from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import get
from conan.tools.layout import basic_layout

class LibVmafRecipe(ConanFile):
    name = "libvmaf"
    version = "3.0.0"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    
    def layout(self):
        basic_layout(self, src_folder="src")
        # Tell Conan the actual meson.build is inside the 'libvmaf' subfolder
        self.folders.source = "src/libvmaf"

    def source(self):
        url = f"https://github.com/Netflix/vmaf/archive/refs/tags/v{self.version}.tar.gz"
        # We MUST extract into the parent folder ('src') so the 'libvmaf' 
        # directory inside the tarball lands perfectly at 'src/libvmaf'.
        base_src = os.path.join(self.source_folder, "..")
        get(self, url, destination=base_src, strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # libvmaf meson.build uses 'default_library' standard meson option
        # which MesonToolchain handles automatically from self.options.shared
        tc.generate()
        
    def build_requirements(self):
        self.tool_requires("meson/1.6.0")
        #if self.settings.arch in ["x86", "x86_64"]:
        #    self.tool_requires("nasm/2.16.01")
    
    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.libs = ["vmaf"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "libvmaf")]
        if self.settings.os == "Windows":
            # MinGW requires explicit linking of the C++ standard library and math library
            self.cpp_info.system_libs.extend(["m", "stdc++"])
        elif self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "stdc++"])
        elif self.settings.os == "Macos":
            self.cpp_info.system_libs.append("c++")
        # This ensures FFmpeg's ./configure finds it easily
        self.cpp_info.set_property("pkg_config_name", "libvmaf")
        self.cpp_info.set_property("cmake_file_name", "libvmaf")

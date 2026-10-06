from conan import ConanFile
from conan.tools.cmake import cmake_layout

class EncodingGuidelines(ConanFile):
    name = "EncodingGuidelines"
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv creates the 'conanrun.sh' script to set your PATH
    generators = "VirtualRunEnv"

    options = {
        "ffmpeg_version": ["6.1.1", "7.1.3", "8.0.1", "8.1", "8.1.1"],
        "shared": [True, False],
        "with_opencolorio": [True, False],
        "with_vmaf": [True, False],
        "with_zimg": [True, False],
        "with_x265": [True, False],
        "with_libaom": [True, False],
    }
    default_options = {
        "ffmpeg_version": "8.1",
        "shared": False,
        "with_opencolorio": True,
        "with_vmaf": True,
        "with_zimg": True,
        "with_x265": False,
        "with_libaom": False,
    }

    def requirements(self):
        if self.options.ffmpeg_version in ["8.1", "8.1.1"]:
            self.requires(f"ffmpeg/{self.options.ffmpeg_version}")
            self.requires("openapv/[>=0.2.0.4]")
            self.requires("openjpeg/2.5.2", run=True)
            self.requires("opencolorio/2.5.1", run=True, force=True)
        elif self.options.ffmpeg_version == "6.1.1":
            self.requires("ffmpeg/6.1.1")
            self.requires("libx264/cci.20240224", run=True)
            self.requires("openjpeg/2.5.2", run=True)
        elif self.options.ffmpeg_version == "7.1.3":
            self.requires("ffmpeg/7.1.3")
            self.requires("libx264/cci.20240224", run=True)
            self.requires("openjpeg/2.5.4", run=True)
        else:
            self.requires("ffmpeg/8.0.1")
            self.requires("libx264/cci.20250910", run=True)
            self.requires("openjpeg/2.5.4", run=True)
        
        # Core dependencies
        self.requires("libvmaf/3.0.0", run=True)
        self.requires("openssl/3.1.7", run=True)
        self.tool_requires("nasm/2.16.01")

        if self.options.with_zimg:
            self.requires("zimg/3.0.5", run=True)
        if self.options.with_x265:
            self.requires("libx265/3.6", run=True)
        if self.options.with_libaom:
            self.requires("libaom-av1/3.6.1", run=True)

    def configure(self):
        ffmpeg = self.options["ffmpeg"]
        # Universal guidelines options
        ffmpeg.with_gpl = True
        ffmpeg.with_version3 = True
        ffmpeg.with_nonfree = True
        ffmpeg.shared = self.options.shared
        
        # Hardware & Frameworks
        ffmpeg.with_videotoolbox = True # --enable-videotoolbox
        
        # External Libraries
        ffmpeg.with_harfbuzz = True     # --enable-libharfbuzz
        ffmpeg.with_freetype = True     # --enable-libfreetype
        ffmpeg.with_libplacebo = True   # --enable-libplacebo
        ffmpeg.with_openapv = True      # --enable-liboapv
        ffmpeg.with_openjpeg = True     # --enable-libopenjpeg
        ffmpeg.with_libvmaf = self.options.with_vmaf
        ffmpeg.with_svtav1 = True       # --enable-libsvtav1
        ffmpeg.with_libx264 = True      # --enable-libx264
        ffmpeg.with_libx265 = self.options.with_x265
        ffmpeg.with_libaom = self.options.with_libaom
        ffmpeg.with_libzimg = self.options.with_zimg
        ffmpeg.with_libvpx = True
        ffmpeg.with_dav1d = True

        # Dependency-specific fixes
        self.options["dav1d"].assembly = False
        self.options["libx265"].assembly = False
        
        # Enable 8.1 specific features
        if self.options.ffmpeg_version in ["8.1", "8.1.1"]:
            ffmpeg.with_opencolorio = self.options.with_opencolorio

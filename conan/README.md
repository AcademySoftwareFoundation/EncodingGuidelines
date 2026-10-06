---
layout: default
nav_order: 5.7
title: Building FFmpeg with Conan
parent: Encoding Overview
---

# Conan Build System

[Conan](https://conan.io) is a multi-platform C/C++ package manager. While its typically used to help build applications, it does provide a nice way to build mutiple versions of applications that can easily be run side by side. For example, you can have multiple versions of ffmpeg installed, and you can switch between them by running the conanrun.bat script in a shell.

We have build profiles for MacOS, Linux and Windows.

## OSX

```bash
cd EncodingGuidelines/conan
source linux-osx-setup.sh # sets up environment variables, installs conan and imports some additional conan recipes for vmaf, OCIO and and updated ffmpeg one to include the OCIO filter
source ffmpeg-8.1-osx-build.sh # Runs the conan build.
```

The resulting build should be in `build-osx/full_deploy/host/ffmpeg/8.1/Release/armv8/bin/ffmpeg`. It should be statically linked so that it can be run on other macs without conan installed.

If you do choose to use the dynamic build, you can create a standalone bundle that can be run on other macs without conan installed by running the following script:

```bash
cd EncodingGuidelines/conan
source ./create-osx-bundle.sh
```

## Linux

If you are building for RHEL 9 / Rocky 9:

```bash
cd EncodingGuidelines/conan
source linux-osx-setup.sh # sets up environment variables, installs conan and imports some additional conan recipes for vmaf, OCIO and and updated ffmpeg one to include the OCIO filter
source ffmpeg-8.1-rhel9-build.sh # Runs the conan build.
```

The resulting build should be in `build-rhel9/full_deploy/host/ffmpeg/8.1/Release/armv8/bin/ffmpeg`. It should be statically linked so that it can be run on other macs without conan installed.

I think this should work on other varients of linux, but I haven't tested it.

If you do choose to use the dynamic build, you can create a standalone bundle that can be run on other macs without conan installed by running the following script:

```bash
cd EncodingGuidelines/conan
source ./create-linux-bundle.sh
```

This will create an `ffmpeg-linux-standalone` folder from the `build-rhel9/full_deploy` output.

## Windows

Windows is the more complex install since ffmpeg requires so many different libraries that require different build environments.
What we have found that works is using the [msys2](https://www.msys2.org/) environment with the mingw toolchain.

Note, this build does not include x265 or aom (AV1). Sadly there are unresolved issues building x265 and aom on Windows so they are currently disabled, although they will be built on linux and MacOS.

zimg is now enabled by default (`with_zimg=True`), which provides the `zscale` filter. This matters for colour accuracy: swscale's `scale` filter has a systematic bias in its full-range to limited-range conversion, so `zscale` is the recommended filter for colour space and range conversions. See [Scaling and colour conversion](../EncodeSwsScale.html) for the measurements. If zimg causes problems in your environment you can still turn it off with `-o with_zimg=False`.

Start by downloading msys2, once its installed, you will be presented with a number of different launch environments. You want to use the one that has "mingw" in the name, e.g. "MSYS2 MinGW 64-bit".

Its worth noting, that the this process works with x86_64, but not with arm64 (although that is something I'm hoping to eventually get working).

I would recommend checking out the [Encoding Guidelines](https://github.com/AcademySoftwareFoundation/EncodingGuidelines) and then going to the conan folder.

There you can run windows_setup.sh to install the required tools and conan.

Once you have that running, you want to run:

```bash
cd EncodingGuidelines/conan
source windows-setup.sh
```

You can then run:

```bash
source windows_ffmpeg_build.sh
```

to build ffmpeg with conan, this will install ffmpeg in the conan/build-windows/full_deploy/host/ffmpeg/ folder.
You can do an initial test of the code by running the build-windows/conanrun.bat script in a shell. This will set up the environment variables so that you can run the ffmpeg executables.

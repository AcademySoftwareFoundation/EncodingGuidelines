---
layout: default
nav_order: 8
title: Building FFMPEG in Docker
parent: Encoding Overview
---

# Building FFMPEG in Docker

## Introduction

The docker containers provide a standard environment to run the test suites in the git repo. This is also a great way to build ffmpeg from scratch.

Its based on <https://github.com/AcademySoftwareFoundation/aswf-docker/blob/master/ci-vfxall/Dockerfile> - providing the the ASWF environment including OCIO and OIIO.
Its using the ffmpeg build environment based on <https://github.com/jrottenberg/ffmpeg.git>, but with vmaf compiled in, and also OIIO rebuilt to include OpenJPH. ACES 1.2 is also checked out, with the python libraries to run the tests.

## Building container

The runme.sh script will mount the git repo as "/test" and create a shell to run the tests in.

### Building for rocky-ffmpeg-8.1

Built on top of Rocky Linux 9 (identical to RHEL 9).
This builds all the components directly not relying on any ASWF containers, including correctly building OCIO and OIIO.

```
cd rocky-ffmpeg-8.1
docker build -t rocky-ffmpeg-8.1 .
./runme.sh
```

There are also earlier builds with ffmpeg 7.1, 7.0, 6.1 and 6.0

### Building for ffmpeg-8.1

Built on top of aswf/ci-vfxall:2026-clang20.3 which is based on rocky-9
This tries to rely on existing VFX containers, so OCIO is not rebuilt.

```
cd ffmpeg-8.1
docker build -t ffmpeg-8.1 .
./runme.sh
```

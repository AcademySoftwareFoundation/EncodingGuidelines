
---
layout: default
nav_order: 5.6
title: Docker Container
parent: Encoding Overview
---

# Docker container for testing.

## Introduction
The docker containers provide a standard environment to run the test suites in the git repo.

Its based on https://github.com/AcademySoftwareFoundation/aswf-docker/blob/master/ci-vfxall/Dockerfile - providing the the ASWF environment including OCIO and OIIO. 
Its using the ffmpeg build environment based on https://github.com/jrottenberg/ffmpeg.git, but with vmaf compiled in, and also OIIO rebuilt to include OIIO. ACES 1.2 is also checked out, with the python libraries to run the tests.


## Building container

The runme.sh script will mount the git repo as "/test" and create a shell to run the tests in.

### Building for ffmpeg-4.4
Built on the ASWF vfxall image.

```
cd ffmpeg-4.4
docker build -t ffmpeg4.4 .
./runme.sh
```


### Building for ffmpeg-5.0
Built on the ASWF vfxall image.

```
cd ffmpeg-5.0
docker build -t ffmpeg5.0 .
./runme.sh
```


### Building for rocky-ffmpeg-5.1
Built on top of Rocky linux i9 (identical to RHEL 9).

```
cd rocky-ffmpeg-5.1
docker build -t ffmpeg5.1 .
./runme.sh
```


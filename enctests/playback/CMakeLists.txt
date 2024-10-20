cmake_minimum_required(VERSION 3.10)
project(codec_test C)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

set(CMAKE_CXX_FLAGS_DEBUG "-g")
set(CMAKE_CXX_FLAGS_RELEASE "-O3")

set(CMAKE_C_STANDARD 11)

if(CMAKE_COMPILER_IS_GNUCXX)
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wpedantic")
endif()

# Find FFmpeg packages
find_package(PkgConfig REQUIRED)
pkg_check_modules(FFMPEG REQUIRED IMPORTED_TARGET
    libavcodec
    libavformat
    libavutil
    libswscale
)

# Add the executable
add_executable(codec_test codec_test.c)

# Link against FFmpeg libraries
target_link_libraries(codec_test PRIVATE PkgConfig::FFMPEG)

# Include FFmpeg headers
target_include_directories(codec_test PRIVATE ${FFMPEG_INCLUDE_DIRS})

# If you're on macOS and using Homebrew, you might need to add this:
if(APPLE)
    include_directories(/opt/homebrew/include)
    link_directories(/opt/homebrew/lib)
endif()

# Add compiler flags
target_compile_options(codec_test PRIVATE -Wall -Wextra -pedantic)

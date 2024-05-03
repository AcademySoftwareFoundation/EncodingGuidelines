GITROOT=`git rev-parse --show-toplevel`
docker run \
  -it \
  --name rocky-ffmpeg-7.0 \
  --mount type=bind,source=${GITROOT},target=/test \
  rocky-ffmpeg-7.0

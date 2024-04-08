GITROOT=`git rev-parse --show-toplevel`
docker run \
  -it \
  --name rocky-ffmpeg-5.1 \
  --mount type=bind,source=${GITROOT},target=/test \
  rocky-ffmpeg-5.1

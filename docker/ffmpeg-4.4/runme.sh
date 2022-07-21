GITROOT=`git rev-parse --show-toplevel`
docker run \
  -it \
  --mount type=bind,source=${GITROOT},target=/test \
  ffmpeg4.4

GITROOT=`git rev-parse --show-toplevel`
docker run \
  -it \
  --name ffmpeg5.0 \
  --mount type=bind,source=${GITROOT},target=/test \
  ffmpeg5.0

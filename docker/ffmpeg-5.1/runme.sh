GITROOT=`git rev-parse --show-toplevel`
docker run \
  -it \
  --name ci-ffmpeg5.0 \
  --mount type=bind,source=${GITROOT},target=/test \
  ci-ffmpeg5.0

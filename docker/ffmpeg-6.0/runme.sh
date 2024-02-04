GITROOT=`git rev-parse --show-toplevel`
docker run \
  -it \
  --name ci-ffmpeg6.0 \
  --mount type=bind,source=${GITROOT},target=/test \
  ci-ffmpeg6.0

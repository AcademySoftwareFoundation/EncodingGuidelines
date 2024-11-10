GITROOT=`git rev-parse --show-toplevel`
docker run \
  -it \
  --name ci-ffmpeg7.1  --gpus=all,capabilities=video \
  --mount type=bind,source=${GITROOT},target=/test \
  ci-ffmpeg7.1

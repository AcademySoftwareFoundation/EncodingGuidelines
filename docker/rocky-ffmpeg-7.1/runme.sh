GITROOT=`git rev-parse --show-toplevel`
docker run \
  -it \
  --name rocky-ffmpeg-7.1  --gpus=all,capabilities=video \
  --mount type=bind,source=${GITROOT},target=/test \
  rocky-ffmpeg-7.1

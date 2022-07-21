GITROOT=`git rev-parse --show-toplevel`
docker run \
  -it \
  --name ffmpeg4.4 \
  --mount type=bind,source=${GITROOT},target=/test \
  ffmpeg4.4

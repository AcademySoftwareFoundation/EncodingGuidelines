GITROOT=`git rev-parse --show-toplevel`
docker run \
  -it \
  --name ffmpeg-5.1 \
  --mount type=bind,source=${GITROOT},target=/test \
  ffmpeg-5.1

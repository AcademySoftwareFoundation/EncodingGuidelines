FOR /F %%a IN ('git rev-parse --show-toplevel') DO SET GITROOT=%%a
echo Mounting: %GITROOT%
docker run -it --name ci-ffmpeg-6.0 --mount type=bind,source=%GITROOT%,target=/test ci-ffmpeg-6.0

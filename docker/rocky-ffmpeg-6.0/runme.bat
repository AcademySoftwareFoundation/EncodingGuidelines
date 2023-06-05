FOR /F %%a IN ('git rev-parse --show-toplevel') DO SET GITROOT=%%a
echo Mounting: %GITROOT%
docker run -it --name ffmpeg-6.0 --mount type=bind,source=%GITROOT%,target=/test ffmpeg-6.0

  curl https://s3.amazonaws.com/senkorasic.com/test-media/video/sintel/source/Sintel-trailer-1080p-png.zip -o Sintel-trailer-1080p-png.zip
  unzip Sintel-trailer-1080p-png.zip -d Sintel-trailer-1080p-png
# from https://commons.wikimedia.org/wiki/File:SMPTE_Color_Bars_16x9.svg  
curl https://upload.wikimedia.org/wikipedia/commons/6/60/SMPTE_Color_Bars_16x9.svg -o SMPTE_Color_Bars.svg
convert -verbose -size 1920x1080 SMPTE_Color_Bars.svg SMPTE_Color_Bars.png

#mkdir -p /usr/local/share/model
#curl https://raw.githubusercontent.com/Netflix/vmaf/master/model/vmaf_v0.6.1.pkl.model -o /usr/local/share/model/vmaf_v0.6.1.pkl.model
#curl https://raw.githubusercontent.com/Netflix/vmaf/master/model/vmaf_v0.6.1.pkl -o /usr/local/share/model/vmaf_v0.6.1.pkl

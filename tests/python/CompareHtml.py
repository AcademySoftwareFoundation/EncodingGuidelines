# Now we build the web page.

# This is a super basic html template file, trying to keep the number of dependancies down for now.

header = """
<html>
<head>
  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
  <script src="https://code.jquery.com/ui/1.13.0/jquery-ui.js"></script>
      <link rel="stylesheet" href="https://code.jquery.com/ui/1.13.0/themes/base/jquery-ui.css">
  <style>
  .grid tbody tr td {{ cursor: grab }}
  </style>
  <script>
  $( function() {{
    if( ! /Android|webOS|iPhone|iPad|iPod|Opera Mini/i.test(navigator.userAgent) ) {{
        $( "#sort tbody" ).sortable();
    $( "#sort2 tbody" ).sortable();
    }}
    var urlargs = document.location.href.split("?")
    if (urlargs.length > 1){{
        $(".index").hide();
        $(urlargs[1]).show();
     }}
  }} );
  </script>
</head>

<body style="background-color:rgb(65 65 65); color:rgb(200,200,200)">
{introduction}
<table id="sort" class="grid"  border=0 cellspacing="1" cellpadding="0">
<tbody>
"""

image_template = """
<TR class="index group{group}"  id="button{id}">
	<TD><img width=25 src="../../static/reorder.png"></td><TD >{label}</TD><td><img src="{image}"/></td>
</TR>
"""
video_template = """
<TR class="index group{group}" id="button{id}">
	<TD><img width=25 src="../../static/reorder.png"></td><TD>{label} {ext}</TD><td><video {videohtml} ><source src='{video}' type='video/mp4'></video></td><td>{cmd}</td>
</TR>
"""

tail = """
</tbody>
</table>

</body>
</html>

"""

def createCompareHtml(outputpath="compare.html", listimages=[], introduction="", videohtml=" width='1024' height='150' "):
	"""
	:param outputpath: output path for htmlfile
	:param listimages: list of dictionaries of things to output. Each item has a "label", and either a "image" or a "video" key.
	:param introduction: An introduction for the top of the file.
	"""

	html = header.format(introduction=introduction)
	for output in listimages:
		if 'group' not in output:
			output['group'] = ""
		if 'id' not in output:
			output['id'] = ""
		if 'cmd' not in output:
			output['cmd'] = ""
		if "image" in output:
			html += image_template.format(**output)
		else:
			output['videohtml'] = videohtml
			output['ext'] = output['video'][-3:]
			html += video_template.format(**output)

	html += tail

	f = open(outputpath, "w")
	f.write(html)
	f.close()

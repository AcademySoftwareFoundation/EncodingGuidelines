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
  .ui-button {{margin: 5px; border-radius: 8px}}
  </style>
  <script>
$(document).ready(function(){{

"""

script_template = """
        $("#button{id}").click( function()
           {{
             $( ".videogroup" ).hide();
			 $( "#{id}" ).show();
           }}
        );
"""

body_begin = """
		$( ".videogroup" ).hide();
		$( "#{id}" ).show();
}});
    </script>

</head>

<body style="background-color:rgb(65 65 65); color:rgb(200,200,200)">
{introduction}

    <div data-role="page" data-theme='a'>

      <div data-role="content"><TABLE><TR><TD width='300' align='center' valign="top">
"""
button_template = """
        <button class="ui-button ui-widget ui-corner-all" id="button{id}" data-role="button">{label}</button><BR/>
"""

image_template = """
<div id="{id}" class="videogroup"><h2>{label}</h2><img  {videohtml} src='{image}'/></div>
"""

video_template = """
<div id="{id}" class="videogroup"><h2>{label}</h2><video {videohtml} ><source src='{video}' type='video/mp4'/></video><p>{cmd}</p></div>
"""

tail = """
      </TD></TR></TABLE>
      </div>

   </div>
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
		html += script_template.format(**output)
	listimages[0]['introduction'] = introduction
	html += body_begin.format(**listimages[0])
	for output in listimages:
		html += button_template.format(**output)
	html += "</div></TD><TD align='left' valign='top'>"
	for output in listimages:
		output['videohtml'] = videohtml
		if 'cmd' not in output:
			output['cmd'] = ''
		if "image" in output:
			html += image_template.format(**output)
		else:
			output['videohtml'] = videohtml
			html += video_template.format(**output)

	html += tail

	f = open(outputpath, "w")
	f.write(html)
	f.close()

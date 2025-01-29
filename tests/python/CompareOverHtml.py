# Now we build the web page.

# This is a super basic html template file, trying to keep the number of dependencies down for now.

header = """
<html>
<head>
  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
  <script src="https://code.jquery.com/ui/1.13.0/jquery-ui.js"></script>
      <link rel="stylesheet" href="https://code.jquery.com/ui/1.13.0/themes/base/jquery-ui.css">
  <style>
  a:link {{
        color:rgb(150, 150, 255);
   }}
     a:visited {{
        color:rgb(120, 120, 255);
   }}
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

<body style="background-color:#27262b; color:rgb(200,200,200)">

{introduction}

    <div data-role="page" data-theme='a'>

      <div data-role="content"><TABLE><TR><TD width='100' align='center' valign="top">
"""
button_template = """
        <button class="ui-button ui-widget ui-corner-all" id="button{id}" data-role="button">{label}</button><BR/>
"""

label_maintemplate = """
        <div ><B>{label}</B></div><BR/>
"""
image_template = """
<div id="{id}" class="videogroup"><h2>{label}</h2><img  {videohtml} src='{image}'/><p>{description}</p><p>{cmd}</p></div>
"""

video_template = """
<div id="{id}" class="videogroup"><h2>{label}</h2><video {videohtml} ><source src='{video}' type='video/mp4'/></video><p>{description}</p><p>{cmd}</p></div>
"""
label_template = """
<div id="{id}" class="videogroup"><h2>{label}</h2><p>{description}</p><p>{cmd}</p></div>
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
	listimages[1]['introduction'] = introduction
	html += body_begin.format(**listimages[1])
	for output in listimages:
		if "video" not in output and 'image' not in output:
			html += label_maintemplate.format(**output)
			continue
		html += button_template.format(**output)
	html += "</div></TD><TD align='left' valign='top'>"
	for output in listimages:
		output['videohtml'] = videohtml
		if 'description' not in output:
			output['description'] = ''
		if 'cmd' not in output:
			output['cmd'] = ''
		if "image" in output:
			html += image_template.format(**output)
		elif "video" not in output:
			html += label_template.format(**output)
		else:
			output['videohtml'] = videohtml
			html += video_template.format(**output)

	html += tail

	f = open(outputpath, "w")
	f.write(html)
	f.close()

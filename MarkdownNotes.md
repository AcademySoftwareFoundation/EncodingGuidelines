# Testing Markdown locally.

To easily preview markdown, we need to setup jekyll as a local server.

1: Install ruby+Devkit [https://rubyinstaller.org/downloads/](https://rubyinstaller.org/downloads/)
2: Install Jekyll [https://jekyllrb.com/docs/installation/windows/](https://jekyllrb.com/docs/installation/windows/)
3: gem install jekyll just-the-docs jekyll-remote

If you are on windows, you may want `gem install wdm` too.


NOTE, there is a separate config file for running it locally where we point to a local install of just-the-docs

you can then run it with:
```console
jekyll serve --incremental -l -o --config _config_local.yml
```
```
/opt/homebrew/lib/ruby/gems/3.4.0/gems/jekyll-4.4.1/exe/jekyll serve --incremental -l -o --config _config_local.yml
```




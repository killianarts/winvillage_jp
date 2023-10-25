#!/bin/bash

dir="base/static/base/js"
hyperscript="https://unpkg.com/hyperscript.org"
htmx="https://unpkg.com/htmx.org"

# Create the directory if it doesn't exist
mkdir -p $dir

# htmx
# Get the URL of the minified script after redirects
htmx_redirect_url=$(curl -Ls -o /dev/null -w %{url_effective} "${htmx}")

# Construct the URL of the non-minified script by replacing '.min.js' with '.js'
htmx_non_minified_url="${htmx_redirect_url/min.js/js}"

# Download the non-minified htmx script using curl
curl -L -o "${dir}/htmx.js" "${htmx_non_minified_url}"

# hyperscript
# Get the URL of the minified script after redirects
hyperscript_redirect_url=$(curl -Ls -o /dev/null -w %{url_effective} "${hyperscript}")

# Construct the URL of the non-minified script by replacing '.min.js' with '.js'
hyperscript_non_minified_url="${hyperscript_redirect_url/min.js/js}"

# Download the non-minified hyperscript using curl
curl -L -o "${dir}/hyperscript.js" "${hyperscript_non_minified_url}"
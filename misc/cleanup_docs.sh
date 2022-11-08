#!/bin/sh

PROJECT_ROOT=$(dirname $(dirname $(readlink -f $0)))
DOCSROOT="$PROJECT_ROOT/docs"

\rm -f "$DOCSROOT/"*.html
\rm -f "$DOCSROOT/"*.inv
\rm -f "$DOCSROOT/"*.js
\rm -fr "$DOCSROOT/_images"
\rm -fr "$DOCSROOT/_sources"
\rm -fr "$DOCSROOT/_static"
\rm -f "$DOCSROOT/".buildinfo


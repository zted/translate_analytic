#!/bin/bash

set -e
cd opt/scripts
python keyword_translator.py "$@"

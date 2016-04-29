#!/bin/bash

cd webapps/poema/htdocs/
git pull --ff
pip install -r requirements.txt
../apache2/bin/restart

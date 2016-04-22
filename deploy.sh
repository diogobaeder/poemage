#!/bin/bash

cd webapps/poema/htdocs/
git pull --ff
../apache2/bin/restart

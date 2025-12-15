#!/bin/bash

cd /mnt/shared/TouchscreenApparatus
source .venv/bin/activate
cd Controller
sudo pigpiod

python WebUI.py

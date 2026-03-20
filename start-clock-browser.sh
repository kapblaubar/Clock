#!/usr/bin/env bash
set -e

export DISPLAY=:0
exec /usr/bin/python3 /home/admin/Clock/native_display.py

#!/bin/sh

go build
python3 data_process.py
./ra2
python3 sort_data.py



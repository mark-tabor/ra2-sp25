#!/bin/sh

python3 data_process.py
go build
./ra2
python3 sort_data.py



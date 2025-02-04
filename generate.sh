#!/bin/sh

go build
python3 data_process.py
for i in {1..10}
do
mkdir data/$i
./ra2
python3 sort_data.py
mv data/out.csv data/$i/out.csv
mv data/stats.txt data/$i/stats.txt
done

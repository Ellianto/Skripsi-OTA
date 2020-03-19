#! /bin/bash

curr_dir=/mnt/d/Projects/Skripsi/Tests/Shell_Scripts
file_src=run.py
gateway_addr_1=192.168.1.12
target_dir=/home/pi/gateway_code/code/run.py

cd $curr_dir

echo 'Beginning update...'

./main_distribute.sh $file_src $gateway_addr_1 $target_dir 192.168.66.174

echo 'Update finished!'
exit 0
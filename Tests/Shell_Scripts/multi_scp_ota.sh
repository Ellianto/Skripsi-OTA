#! /bin/bash

curr_dir=/mnt/d/Projects/Skripsi/Tests/Shell_Scripts
file_src=run.py
gateway_addr_1=192.168.1.3
gateway_addr_2=192.168.1.2
target_dir=/home/pi/gateway_code/code/

cd $curr_dir

echo 'Beginning update...'

./main_distribute.sh $file_src $gateway_addr_1 $target_dir 192.168.66.174
./main_distribute.sh $file_src $gateway_addr_2 $target_dir 192.168.67.4

echo 'Update finished!'
exit 0
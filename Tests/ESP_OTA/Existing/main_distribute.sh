#! /bin/bash

# Place it in gateway_code directory

# Requires : sshpass and putty's plink

# Sends the file to end devices
passwd=teknik_komputer

gw_01_ip=192.168.1.12
# gw_02_ip=192.168.1.

echo 'Beginning Update'

echo 'Removing old code...'
plink pi@$gw_01_ip -pw $passwd rm /home/pi/gateway_code/code/run.ino.nodemcu.bin
# plink pi@$gw_02_ip -pw $passwd "rm /home/pi/gateway_code/code/run.ino.nodemcu.bin"

echo 'Replacing with new code...'
sshpass -p $passwd scp /mnt/d/Projects/Skripsi/Tests/ESP_OTA/Existing/run.ino.nodemcu.bin pi@$gw_01_ip:/home/pi/gateway_code/code/run.ino.nodemcu.bin
# sshpass -p $passwd scp  "pi@$gw_02_ip:/home/pi/gateway_code/code/run.ino.nodemcu.bin"

echo 'Sending to end device...'
plink pi@$gw_01_ip -pw $passwd python3 /home/pi/gateway_code/code/espotabatch.py && exit
# plink pi@gw_02_ip -pw $passwd "python3 /home/pi/gateway_code/code/espotabatch.py"

echo 'Update Complete'
exit 0

target_file=/home/pi/gateway_code/code/run.ino.nodemcu.bin
esp_ota=/home/pi/gateway_code/code/espota.py

my_ip=192.168.66.1
target_port=8266

echo "Updating ESPs:"

python3 $esp_ota -I $my_ip -p $target_port -i 192.168.66.48 -f $target_file
# python3 $target_file -I $my_ip -P $my_port -p $target_port -i 192.168.66.48 -f $target_file

echo 'Done!'
exit 0

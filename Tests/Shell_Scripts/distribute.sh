
# Place it in gateway_code directory

# Requires : sshpass and putty's plink

# Sends the file to end devices
passwd=teknik_komputer

# $1 : File source 
# $2 : Target End Device Address

echo "Updating $2:"

echo 'Removing old code...'
plink pi@$2 -pw $passwd "rm /home/pi/end_device_code/code/run.py"

echo 'Replacing with new code...'
sshpass -p $passwd scp $1 pi@$2:/home/pi/end_device_code/code/run.py

echo 'Running new code...'
plink pi@$2 -pw $passwd -m /home/pi/gateway_code/commands.txt

# Create a commands.txt containing the following:
    # nohup python3 /home/pi/end_device_code/code/run.py &>/dev/null &
    # exit

echo 'Done!'
exit 0

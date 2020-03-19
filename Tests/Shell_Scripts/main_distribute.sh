#! /bin/bash

# Place it in gateway_code directory

# Requires : sshpass and putty's plink

# Sends the file to end devices
passwd=teknik_komputer

# $1 : File Source
# $2 : Target Gateway address
# $3 : File Directory Destination
# $4 : Target End Device Address

echo 'Beginning Update'

echo 'Removing old code...'
plink pi@$2 -pw $passwd "rm $3$1"

echo 'Replacing with new code...'
sshpass -p $passwd scp $1 pi@$2:$3$1

echo 'Sending to end device...'
plink pi@$2 -pw $passwd "/home/pi/gateway_code/distribute.sh $3$1 $4"

echo 'Update Complete'
exit 0

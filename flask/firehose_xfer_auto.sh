set -x
echo "DATA PATH " $1
echo "TEMP PATH " $2
echo "NODE " $3
echo "HOST" $4
echo "PW" $5
drf cp --nodrf --drfprops $1 $2
drf mv --nodrfprops $1 $2
rsync -ratlzvm --remove-source-files --rsh="/usr/bin/sshpass -p $5 ssh -o StrictHostKeyChecking=no -l $3"  $2 $3@$4:/home/$3/TangerineData


#!/bin/bash
# Zombie processes killing script.
# Must be run under root.
case "$1" in
--admin)
        mapfile -t stat < <(ps -xal | grep '<defunct>' | awk '{print $4, $10}' | grep 'Z' | awk '{print $1}')

        if ((${#stat} > 0));then
    	    echo zombie processes found:
	    echo .
	    ps -xal | grep '<defunct>' | awk '{print $4, $10, $13}' | grep 'Z' | awk '{print $1,$2,$3}'
	    echo -n "Kill zombies? [y/n]: "
	    read keyb
	    if [ $keyb == 'y' ];then
		echo killing zombies..
		for i in "${stat[@]}"
		  do
		   echo $i
		   kill -9 $i
		  done
	    fi
	else
	    echo no zombies found!
	fi
;;
--cron)
	stat=`ps ax | awk '{print $1}' | grep -v "PID" | xargs -n 1 ps lOp | grep -v "UID" | awk '{print"pid: "$3" *** parent_pid: "$4" *** status: "$10" *** process: "$13}' | grep ": Z"`
        if ((${#stat} > 0));then
        ps ax | awk '{print $1}' | grep -v "PID" | xargs -n 1 ps lOp | grep -v "UID" | awk '{print$4" status:"$10}' | grep "status:Z" | awk '{print $1}' | xargs -n 1 kill -9
	echo `date`": killed some zombie proceses!" >> /var/log/zombies.log
	fi
;;
*)	echo 'usage: zombies {--cron|--admin}'
;;
esac
exit 0

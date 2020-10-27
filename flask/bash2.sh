#!/bin/bash
set $first = $1
set $second = $2


if [ "$1" -eq 0 ] && [ "$2" -eq 0 ]
then
	echo "Num1 and Num2 are zero"
elif [ $first -eq $second ]
then
	echo "Both Values are equal"
elif [ $first -gt $second ]
then
	echo "$first is greater than $second"
else
	echo "$first is lesser than $second"
fi

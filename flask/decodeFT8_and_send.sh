set -x #echo on
nice -n10 ./ft8d_del $6 > $1/FT8/decoded$2.txt

nice -n10 sort -nr -k 4,4 $1/FT8/decoded$2.txt | awk '!seen[$1"_"$2"_"int($6)"_"$7] {print} {++seen[$1"_"$2"_"int($6)"_"$7]}' | sort -n -k 1,1 -k 2,2 -k 6,6 -o  $1/FT8/decoded$2z.txt
t=1

if [ "$7" = "1" ]
then
 nice -n9 ./upload-to-pskreporter $3 $4 $8 $1/FT8/decoded$2z.txt
else 
 echo Spot uploading off
fi
rm $1/FT8/decoded$2.txt

 

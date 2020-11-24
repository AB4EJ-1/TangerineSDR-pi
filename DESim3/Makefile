all: DEctl DEmain2

DEctl: DEctl.c
	gcc DEctl.c -o DEctl  -I/home/odroid/projects/TangerineSDR-pi/includes  -lpthread -lm

DEmain2: DEmain2.c
	gcc DEmain2.c -o DEmain2 -I/home/odroid/projects/TangerineSDR-pi/includes -lpthread -lm -lfftw3 -lfftw3f

                                     

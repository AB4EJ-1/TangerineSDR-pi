all: rgrcvr upload ft8rcvr wsprrcvr

rgrcvr: rgrcvr.c
	h5cc rgrcvr.c readconfig.c  -o rgrcvr -I/usr/local/include/digital_rf -I/home/ubuntu/projects/TangerineSDR-pi/includes -lconfig -l:libhdf5.so -ldigital_rf -lpthread -lm -lfftw3 -lfftw3f

upload: upload-to-pskreporter.c
	gcc -D_GNU_SOURCE  upload-to-pskreporter.c -o upload-to-pskreporter

ft8rcvr: ft8rcvr.c
	gcc ft8rcvr.c readconfig.c -o ft8rcvr  -I/home/ubuntu/projects/TangerineSDR-pi/includes -lconfig

wsprrcvr: wsprrcvr.c
	gcc wsprrcvr.c readconfig.c -o wsprrcvr  -I/home/ubuntu/projects/TangerineSDR-pi/includes -lconfig -lpthread


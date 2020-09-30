gcc -c -fPIC udpdiscover1.c -o discoverylib.o
gcc -shared discoverylib.o -o discoverylib.so

gcc -c -fPIC udpdiscover1.c -o mylib.o
gcc -shared mylib.o -o mylib.so

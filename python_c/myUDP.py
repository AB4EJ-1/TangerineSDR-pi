""" Python wrapper for the C shared library mylib"""
import sys, platform
import ctypes, ctypes.util


from ctypes import *

# Find the library and load it
    
print("try a loadlibrary")

#cdll.LoadLibrary("./mylib.so")
libc = CDLL("./mylib.so")
print("libc=",libc)

a = c_ulong(0)
m = ctypes.create_string_buffer(212)
UDPdiscover = libc.UDPdiscover
UDPdiscover.argtypes = [ctypes.POINTER(type(m)), ctypes.POINTER(ctypes.c_ulong)]
UDPdiscover.restype = None

print("try to discover")
libc.UDPdiscover(m,a);
print("port a = ", a.value)
print("m=")
print(m.value)
print(sizeof(m), repr(m.raw))



print("done")

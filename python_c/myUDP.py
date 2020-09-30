""" Python wrapper for the C shared library mylib"""
import sys, platform
import ctypes, ctypes.util

from ctypes import *

# Access the shared library (i.e., *.so)
libc = CDLL("./discoverylib.so")
print("libc=",libc)

a = c_ulong(0)
b = c_ulong(0);
m = ctypes.create_string_buffer(16)
UDPdiscover = libc.UDPdiscover
UDPdiscover.argtypes = [ctypes.POINTER(type(m)), ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong)]
UDPdiscover.restype = None

print("Run UDPdiscovery")
libc.UDPdiscover(m,a,b);
print("My port (port A) =",a.value)
print("Tangerine at IP address %s" % m.value.decode("utf-8"))
print("At port B = ", b.value)

print("done")

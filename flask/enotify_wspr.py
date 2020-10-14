# Copyright (C) 2019, 2020 The University of Alabama, Tuscaloosa, AL 35487
# Author: William (Bill) Engelke, AB4EJ
# With funding from the UA Center for Advanced Public Safety and 
# The National Science Foundation.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# About this program:
# Purpose: this program reads in a decoded WSPR text file, parses it, finds all the heard calls
# and grids; then compares these to a list of monitored calls from the config,ini file.
# If it detects a monitored call/grid in the list of heard calls/grids, it will attempt to
# send an email to the configured emnail address using the configuree email server.


import sys
import configparser
import smtplib
from email.mime.multipart import MIMEMultipart 
from email.mime.text import MIMEText 
import os
import os.path, time
import datetime
from datetime import datetime

print ("#args=",len(sys.argv))
print ("args = ",str(sys.argv)) # argv[1] is streamID

p = open('/home/ubuntu/Documents/smtp2go.pw','r')
smtp2gopw = p.read()
smtp2gopw = smtp2gopw[0:(len(smtp2gopw) - 1)] # strip the CR from end
print("pw='"+ smtp2gopw + "'")

parser = configparser.ConfigParser(allow_no_value=True)
parser.read('config.ini')
path = parser['settings']['ramdisk_path'] + "/WSPR/"
print("path=",path)

calltarget = []
gridtarget = []
for call in range(0,6):
  c = parser['monitor']['c' + str(call)]
  if( c != 'None' and len(c) > 0):
    calltarget.append(c)
    
for grid in range(0,6):
  c = parser['monitor']['g' + str(grid)]
  if ( c != 'None' and len(c) > 0):
    gridtarget.append(c)

print("call list",calltarget)

calllist = []
freqlist = []
timelist = []
gridlist = []
with open(path + "decoded" + sys.argv[1] + "z.txt" ,'r') as f:
  for line in f:
    spot = line.split()  
    print(len(spot)) # len >= 8 means a grid was received
    print("date ",spot[0]," time ",spot[1], " freq ", spot[5], " call ", spot[6])
    print("yr:" + spot[0][0:2] + "  mo:" + spot[0][2:4] + " dy:" + spot[0][4:6] + " hr:" + spot[1][0:2] + " min:" + spot[1][2:4])
    datetime = "yr:" + spot[0][0:2] + "  mo:" + spot[0][2:4] + " dy:" + spot[0][4:6] + " hr:" + spot[1][0:2] + " min:" + spot[1][2:4] + " Z "
    print("call " + spot[6] + " freq:", spot[5] ,"MHz")
    freq = spot[5]
    datetime =  "20" +  spot[0][0:2] + "/" + spot[0][2:4] + "/" + spot[0][4:6] + " time: " + spot[1][0:2] + ":" + spot[1][2:4] + " Z"
    print(".")
    calllist.append(spot[6])
    freqlist.append(freq)
    timelist.append(datetime)
    if(len(spot) >= 8):
      gridlist.append(spot[7])
    else:
      gridlist.append("No grid")

print("calls heard", calllist)
detected_list = []

h = -1
for heard in calllist:
  h = h + 1
  for target in calltarget:
    if(heard == target):
      print("target call detected:", target)
      detected_list.append("CALL ALERT - " + heard + " on " + str(freqlist[h]) + " (WSPR) at " + timelist[h])

print("grids heard",gridlist)
print("freqlist ", freqlist)
print("timelist ",timelist)
h = -1
for heard in gridlist:
  h = h + 1
  for target in gridtarget:
    print("h=",h, target)
    if(heard == target):
      print("target grid detected:", target, h)
      detected_list.append("GRID ALERT - " + heard + " on " + str(freqlist[h]) + " (WSPR) at " + timelist[h])
      
    
#print("detected list:")
#print(detected_list)
report = ""
for msg in detected_list:
  report = report + (msg + "\n")
  
print("report:")
print(report)


if(len(detected_list) > 0): 
# SMTP stuff

#Establish SMTP Connection
  s = smtplib.SMTP('smtp2go.com', 2525) 
  print("start tls") 
#Start TLS based SMTP Session
  s.starttls() 
  print("login")
#Login Using Your Email ID & Password
  s.login("engelke77@bellsouth.net", smtp2gopw)

  sender = "engelke77@bellsouth.net"
  receivers = ['engelke77@bellsoutn.net']


  message = """From: From Your Tangerine <engelke77@bellsouth.net>
To: To AB4EJ <engelke77@bellsouth.net>
Subject: Station(s) and/or grid(s) heard

 """ + report + """ --end-- 
"""
  print("send")
  try:
     s.sendmail("engelke77@bellsouth.net","engelke77@bellsouth.net",message)
     s.quit()
  except SMTPException:
   print ("Error: unable to send email")






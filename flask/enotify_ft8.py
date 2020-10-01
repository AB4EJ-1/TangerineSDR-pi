
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
print ("args = ",str(sys.argv))

parser = configparser.ConfigParser(allow_no_value=True)
parser.read('config.ini')
ft8path = parser['settings']['ramdisk_path'] + "/FT8/"
print("path=",ft8path)

#decoded_file = open(ft8path + "decoded" + sys.argv[1] + ".txt" )
#line = decoded_file.readline()
#print(line)
#decoded_file.close()
#spot = line.split()


with open(ft8path + "decoded" + sys.argv[1] + ".txt" ,'r') as f:
  for line in f:
    spot = line.split()  
    print(len(spot)) # len = 8 means a grid was received
    print("date ",spot[0]," time ",spot[1], " freq ", spot[5], " call ", spot[6])
    print("yr:" + spot[0][0:2] + "  mo:" + spot[0][2:4] + " dy:" + spot[0][4:6] + " hr:" + spot[1][0:2] + " min:" + spot[1][2:4])
    print("call " + spot[6] + " freq:", int(spot[5]) / 1000000.0 ,"MHz")
    freq = int(spot[5]) / 1000000.0
    datetime =  "20" +  spot[0][0:2] + "/" + spot[0][2:4] + "/" + spot[0][4:6] + "time: " + spot[1][0:2] + ":" + spot[1][2:4] + " Z"
    print(".")

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
Subject: SMTP e-mail test

Station """ + spot[6] + """ heard at """ + datetime + """ on """ + str(freq) + """ MHz 
"""
print("send")
try:
   s.sendmail("engelke77@bellsouth.net","engelke77@bellsouth.net",message)
   s.quit()
except SMTPException:
   print ("Error: unable to send email")






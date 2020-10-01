from flask import Flask, flash, redirect, render_template, request, session, abort, jsonify, Response
import simplejson as json
import socket
import _thread
import time
import os
import os.path, time
import subprocess
from subprocess import Popen, PIPE
import configparser
import smtplib

import sys, platform
import ctypes, ctypes.util

from ctypes import *

import h5py
import numpy as np
import datetime
from datetime import datetime
import threading

#from array import *
from email.mime.multipart import MIMEMultipart 
from email.mime.text import MIMEText 
from extensions import csrf
from config import Config
from flask_wtf import Form
# following is for future flask upgrade
#from FlaskForm import Form
from wtforms import TextField, IntegerField, TextAreaField, SubmitField, RadioField, SelectField, DecimalField, FloatField
from flask import request, flash
from forms import MainControlForm, ThrottleControlForm, ChannelControlForm, ServerControlForm
from forms import CallsignForm
from forms import ChannelControlForm, ChannelForm, ChannelListForm

from wtforms import validators, ValidationError

from flask_wtf import CSRFProtect

from pyhamtools import locator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'here-is-your-secret-key-ghost-rider'
app.secret_key = 'development key'
app.config.from_object(Config)
csrf.init_app(app)

global theStatus, theDataStatus, thePropStatus, statusmain
global statusFT8, statusWSPR, statusRG, statusSnap, statusFHR
global DE_IP_addr, DE_IP_portB, DE_portB_socket, LH_IP_portA, DE_IP_portC, LH_IP_portF   # portC will be a list (by channelNo)l portF comes from config.ini

# statusControl = 0
received = ""
dataCollStatus = 0;
theStatus = "Not yet started"
theDataStatus = ""
thePropStatus = 0
statusFT8 = 0
statusWSPR = 0
statusRG = 0
statusSnap = 0
statusFHR = 0
statusmain = 0
global tcp_client
f = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

# Here are commands that can be sent to mainctl and forwarded to DE.
# These must be the same as the corresponding mnemonics in the de_signals.h file
# used for mainctl compilation (also DESimulator, if simulator is being used)
STATUS_INQUIRY     = "S?"
DATARATE_INQUIRY   = "R?"
DATARATE_RESPONSE  = "DR"
LED1_ON            = "Y1"
LED1_OFF           = "N1"
TIME_INQUIRY       = "T?"
TIME_STAMP         = "TS"
CREATE_CHANNEL     = "CC"
CONFIG_CHANNEL     = "CH"   # This sets up one channel, which may contain mutiple subchannels
UNDEFINE_CHANNEL   = "UC"
FIREHOSE_SERVER    = "FH"
START_DATA_COLL    = "SC"
STOP_DATA_COLL     = "XC"
DEFINE_FT8_CHAN    = "FT"
START_FT8_COLL     = "SF"
STOP_FT8_COLL      = "XF"
START_WSPR_COLL    = "SW"
STOP_WSPR_COLL     = "XW"
LED_SET            = "SB"  
UNLINK             = "UL"
HALT_DE            = "XX"


def is_numeric(s):
  try:
   float(s)
   return True
  except ValueError:
   print("Value error")
   return False

def send_to_DE(channelNo, msg):
  global DE_IP_addr, DE_IP_portB, DE_portB_socket, LH_IP_portA, DE_IP_portC, LH_IP_portF 
  print("Send to DE ",DE_IP_addr, DE_IP_portC[channelNo], msg)
  msg1 = msg.encode('utf-8')
  DE_portC_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  s = DE_portC_socket.sendto(msg1, (DE_IP_addr, int(DE_IP_portC[channelNo])))
  print("s=",s)
  DE_portC_socket.close()
  return


def create_channel(channelNo, configPort, dataPort):
  global DE_IP_addr, DE_IP_portB, DE_portB_socket, LH_IP_portA, DE_IP_portC, LH_IP_portF  

  msg = bytes(CREATE_CHANNEL + " " + str(channelNo) + " " + str(configPort) + " " + str(dataPort),'utf-8')

  LH_portA_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);

  print("Channel ", channelNo, " Send CREATE_CHANNEL to DE: ",msg, " args = ",DE_IP_addr, DE_IP_portB)
  DE_portB_socket.sendto(msg,(DE_IP_addr, DE_IP_portB))
  print("bind to port ",LH_IP_portA)
  LH_portA_socket.bind(('', LH_IP_portA))

  print("Awaiting reply on port", LH_IP_portA )
  reply = LH_portA_socket.recvfrom(20)
  r = reply[0]

  r = r.decode('utf-8')
  rlist = r.split(" ")
  DE_IP_portC.append(rlist[2]) # element 2 of split string is the PortC sent in the AK by the DE
  print("DE replied: ",r," will send commands for this channel to port ",rlist[2])
  LH_portA_socket.close();
  return 
  

def discover_DE(): # Here we call the UDPdiscover C routine to find fist Tangerine on network
  global DE_IP_addr, DE_IP_portB, LH_IP_portA

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
  DE_IP_addr = m.value.decode("utf-8")
  DE_IP_portB = b.value
  LH_IP_portA = a.value
  print("My port (port A) =",LH_IP_portA)
  print("Tangerine at IP address %s" % DE_IP_addr)
  print("At port B = ", DE_IP_portB)
  return

def send_configuration():
  print("set up configuration")
  parser = configparser.ConfigParser(allow_no_value=True)
  parser.read('config.ini')
  noChannels = parser['channels']['numchannels']

# set up data acquisition. This is always Channel 0, with multiple subchannels.
  msg = "CH 0 VT "+ noChannels + " " + parser['channels']['datarate'] + " " # specify VITA-T (interleaved IQ smaples)
  subchannel_list = ""
  count = 0
  while count < int(noChannels):  # this is actually the no. of data acquisition subchannels
    ant = parser['channels']['p' + str(count)]
    freq = parser['channels']['f' + str(count)]
    subchannel_list = subchannel_list + str(count) + " " + ant + " " + freq + " "
    count = count + 1
  msg = msg + subchannel_list
  print("config 0 =", msg)
  send_to_DE(0, msg)

# set up FT8
  msg = "CH 1 V4 "
  subchannel_list = ""
  count = 0
  for chNo in range(0,7) :
    if parser['settings']['ftant' + str(chNo)] == "Off":
      continue
    subchannel_list = subchannel_list + str(chNo) + " " + parser['settings']['ftant' + str(chNo)] + " " + parser['settings']['ft8'  + str(chNo) + "f"] + " "
    count = count + 1 # how many subchannels are active
  msg = msg + str(count) + " 4000 " + subchannel_list
  print("config 1 (FT8)=",msg)
  send_to_DE(1,msg)

# set up WSPR
  msg = "CH 2 V4 "
  subchannel_list = ""
  count = 0
  for chNo in range(0,7) :
    if parser['settings']['wsant' + str(chNo)] == "Off":
      continue
    subchannel_list = subchannel_list + str(chNo) + " " + parser['settings']['wsant' + str(chNo)] + " " + parser['settings']['ws'  + str(chNo) + "f"]  + " "
    count = count + 1 # how many subchannels are active
  msg = msg + str(count) + " 375 " + subchannel_list
  print("config 2 (WSPR)=",msg)
  send_to_DE(2,msg)
  return
  
  

    

#####################################################################
# Here is the home page (Tangerine.html)
@app.route("/", methods = ['GET', 'POST'])
def sdr():
   form = MainControlForm()
   global theStatus, theDataStatus, tcp_client, statusmain
   global statusFT8, statusWSPR, statusRG, statusSnap, statusFHR
   parser = configparser.ConfigParser(allow_no_value=True)
   parser.read('config.ini')

   if request.method == 'GET':  
     if(parser['settings']['FT8_mode'] == "On"):
       form.propFT.data = True
     else:
       form.propFT.data  = False
     if(parser['settings']['WSPR_mode'] == "On"):
       form.propWS.data = True
     else:
       form.propWS.data  = False
     if(parser['settings']['ringbuffer_mode'] == "On"):
       form.modeR.data = True
     else:
       form.modeR.data  = False
     if(parser['settings']['snapshotter_mode'] == "On"):
       form.modeS.data = True
     else:
       form.modeS.data  = False
     if(parser['settings']['firehoser_mode'] == "On"):
       form.modeF.data = True
     else:
       form.modeF.data  = False

     form.destatus = theStatus
     form.dataStat = theDataStatus
     print("F: home page, status = ",theStatus)
     return render_template('tangerine.html',form = form)

   if request.method == 'POST':
 #     print("F: Main control POST; mode set to ",form.mode.data)
      print("F: Main control POST; modeR=",form.modeR.data)
      print("F: Main control POST; modeS=",form.modeS.data)
      print("F: Main control POST; modeF=",form.modeF.data)
      form.errline = ""
      print("Entering main route")
      print("restart button -",form.restartDE.data)
      result = request.form
      

      if(form.restartDE.data):
      # TODO: here, add code to stop all activities & reflect that in config
        return redirect('/restart')
        
 # Check for errors and missing configurations

      if (form.modeR.data == True and form.modeF.data == True):
        print("F: error - user selected both ringbuffer and firehose")
        form.errline = "Select EITHER Ringbuffer or Firehose mode"
        return render_template('tangerine.html', form = form)

# Other checks to be added include - paths/directories exist for all selected outputs;
#  URL for Central Control; at least one subchannel setup exists

# Set configuration to reflect current settings.

      print("F: setting config for modes")
      if(form.modeR.data == True):
        parser.set('settings','ringbuffer_mode','On')
      else:
        parser.set('settings','ringbuffer_mode','Off')

      if(form.modeS.data == True):
        parser.set('settings','snapshotter_mode','On')
      else:
        parser.set('settings','snapshotter_mode','Off')

      if(form.modeF.data == True):
        parser.set('settings','firehoser_mode','On')
      else:
        parser.set('settings','firehoser_mode','Off')

      if(form.propFT.data == True):
        parser.set('settings','FT8_mode','On')
      else:
        parser.set('settings','FT8_mode','Off')

      if(form.propWS.data == True):
        parser.set('settings','WSPR_mode','On')
      else:
        parser.set('settings','WSPR_mode','Off')

      fp = open('config.ini','w')
      parser.write(fp)
      fp.close()
      print('F: start set to ',form.startDC.data)
      print('F: stop set to ', form.stopDC.data)

# following code is a demo for how to make GNURadio show FFT of a file.
# file name is temporarily hard-coded in displayFFT.py routine
 #        if(form.startDC.data and form.mode.data =='snapshotter'):
  #         process = subprocess.Popen(["./displayFFT.py","/mnt/RAM_disk/snap/fn.dat"], stdout = PIPE, stderr=PIPE)
#           stdout, stderr = process.communicate()
#           print(stdout)
#        return  render_template('tangerine.html', form = form)

      if(form.startDC.data ): # User clicked button to start ringbuffer-type data collection

      #      if(statusmain != 1):
      #        print("F: user tried to start data collection before starting mainctl")
      #        form.errline = "ERROR. You must Start/restart mainctl before starting data collection"
      #        return render_template('tangerine.html', form = form)

            if   ( len(parser['settings']['firehoser_path']) < 1 
                   and form.mode.data == 'firehoseR') :
              print("F: configured temp firehose path='", parser['settings']['firehoser_path'],"'", len(parser['settings']['firehoser_path']))
              form.errline = 'ERROR: Path to temporary firehoseR storage not configured'
            elif ( len(parser['settings']['ringbuffer_path']) < 1 
                   and form.mode.data == 'ringbuffer') :
              print("F: configured ringbuffer path='", parser['settings']['ringbuffer_path'],"'", len(parser['settings']['ringbuffer_path']))
              form.errline = 'ERROR: Path to digital data storage not configured'
            else:

          # User wants to start data collection. Is there an existing drf_properties file?
          # If so, we delete it so that system will build a new one reflecting
          # current settings.

              now = datetime.now()
 
              if(form.mode.data == 'firehoseR'):
                metadataPath = parser['settings']['firehoser_path']
              else:
                metadataPath = parser['settings']['ringbuffer_path']
           #   print("metadata path="+metadataPath)
              print("F: SEND START DATA COLLECTION COMMAND, directory=" + metadataPath)
              returned_value = os.system("mkdir "+ metadataPath)
              print("F: after metadata creation, retcode=",returned_value)

          
          # kill any running rgrcvr processes
              returned_value = os.system("pwd")
              print("kill previous rgrcvr, if any")
              returned_value = os.system("killall -9 rgrcvr")
              print("F: after kill of rgrcvr, retcode=",returned_value)
              returned_value = os.system("./rgrcvr &")      
              print("F: after start of rgrcvr, retcode=",returned_value) 
              send_to_DE(0,START_DATA_COLL + " 0")         
                    
              if(parser['settings']['snapshotter_mode'] == "On"):
                statusSnap = 1
              else:
                statusSnap = 0 
              if(parser['settings']['ringbuffer_mode'] == "On"):
                statusRG = 1
              else:
                statusRG = 0 

              dataCollStatus = 1
# write metadata describing channels into the drf_properties file
              ant = []
              chf = []
              chcount = int(parser['channels']['numchannels'])
              datarate = int(parser['channels']['datarate'])
              for i in range(0,chcount):
                ant.append(int(parser['channels']['p' + str(i)]))
                chf.append(float(parser['channels']['f' + str(i)]))
              print("Record list of subchannels=",chf)
              
              try:
                time.sleep(1)  #wait for properties file to be created
           #     metadataPath = parser['settings']['ringbuffer_path'] + "/" + subdir
                print("Update properties file at ",metadataPath)

                f5 = h5py.File(metadataPath + '/drf_properties.h5','r+')
                f5.attrs.__setitem__('subchannel_frequencies_MHz', chf)
                f5.attrs.__setitem__('data_source',"TangerineSDR")
                f5.attrs.__setitem__('antenna_ports',ant)
                f5.close()
              except Exception as e: 
                print(e)
                theStatus = "Properties file update error " + str(e)
                print("WARNING: unable to update DRF HDF5 properties file")

      if(form.stopDC.data ):
            send_to_DE(0,STOP_DATA_COLL + " 0") 
            returned_value = os.system("killall -9 rgrcvr")
            print("F: after kill of ft8rcvr, retcode=",returned_value) 
            dataCollStatus = 0
            statusRG = 0
            statusSnap = 0

      if(form.startprop.data):  # user hit button to start propagation monitoring

    #    if(statusmain != 1):
    #       print("F: user tried to start data collection before starting mainctl")
    #       form.errline = "ERROR. You must Start/restart mainctl before starting FT8?WSPR"
    #       return render_template('tangerine.html', form = form)

        if(form.propFT.data == True):
            #send_to_mainctl(START_FT8_COLL,0)
            print("kill previous ft8rcvr, if any")
            RAMpath = parser['settings']['ramdisk_path'] + "/FT8"
            returned_value = os.system("mkdir " + RAMpath)
            returned_value = os.system("rm " + RAMpath + "/*.c2")
            returned_value = os.system("killall -9 ft8rcvr")
            print("F: after kill of ft8rcvr, retcode=",returned_value)
            returned_value = os.system("./ft8rcvr &")      
            print("F: after start of ft8rcvr, retcode=",returned_value) 
            send_to_DE(1,START_DATA_COLL + " 1") 
            statusFT8 = 1
            
        if(form.propWS.data == True):
            print("kill previous wsprrcvr, if any")
            RAMpath = parser['settings']['ramdisk_path'] + "/WSPR"
            returned_value = os.system("mkdir " + RAMpath)
            returned_value = os.system("rm " + RAMpath + "/*.c2")
            returned_value = os.system("killall -9 wsprrcvr")
            print("F: after kill of wsprrcvr, retcode=",returned_value)
            returned_value = os.system("./wsprrcvr &")      
            print("F: after start of wsprrcvr, retcode=",returned_value) 
            send_to_DE(2,START_DATA_COLL + " 2") 
            statusWSPR = 1
        thePropStatus = 1

      if(form.stopprop.data) :
        if(form.propFT.data == True):
         #   send_to_mainctl(STOP_FT8_COLL,0)
            returned_value = os.system("killall -9 ft8rcvr")
            print("F: after kill of ft8rcvr, retcode=",returned_value)
            send_to_DE(1,STOP_DATA_COLL + " 1")
            statusFT8 = 0
        if(form.propWS.data == True):
            returned_value = os.system("killall -9 wsprrcvr")
            print("F: after kill of wsprrcvr, retcode=",returned_value)
            send_to_DE(2,STOP_DATA_COLL + " 2")
            statusWSPR = 0
        thePropStatus = 0

      theDataStatus = ""
   #   print("configured modes RG '"+parser['settings']['ringbuffer_mode']+"' Snap '"+parser['settings']['snapshotter_mode']+"'");
   #   if(parser['settings']['ringbuffer_mode'] == "On"):
  #    theDataStatus = theDataStatus + "Ringbuffer " + parser['settings']['ringbuffer_mode'] +";"
      if(statusFT8 == 1):
        theDataStatus = theDataStatus + "FT8 active; "
      if(statusWSPR == 1):
        theDataStatus = theDataStatus + "WSPR active; "
      if(statusRG == 1):
        theDataStatus = theDataStatus + "Ringbuffer active; "
      if(statusSnap == 1):
        theDataStatus = theDataStatus + "Snapshotter active; "
        
      if(statusFHR == 1):
        theDataStatus = theDataStatus + "Firehose-R active"

      print("F: end of control loop; theStatus=", theStatus)
      form.destatus = theStatus
      form.dataStat = theDataStatus
      return render_template('tangerine.html', form = form)

@app.route("/restart") # Starts/restarts DE
def restart():
  global theStatus, theDataStatus, statusmain, dataCollStatus
  global DE_IP_addr, DE_IP_portB, DE_portB_socket, DE_IP_portC, LH_IP_portF # portC and portF are lists (one set per channel)

  DE_IP_portC = [] 
  LH_IP_portF = []
  parser = configparser.ConfigParser(allow_no_value=True)
  parser.read('config.ini')
  print("F: restart; run discovery")

  discover_DE()

  print("RESTART: status = ",theStatus, " received = ", received)
  time.sleep(0.5)
  dataCollStatus = int(parser['settings']['datacollstatus'])
  try:
    print("F: define socket")
    DE_portB_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("F: *DE_portB_socket created ")
    count = 0
    while count < 3:
       cport = parser['settings']['configport' + str(count)]
       dport = parser['settings']['dataport' + str(count)]
       print("create channel with ports ",cport, dport)
       create_channel(count, cport, dport)
       time.sleep(1)
       count = count + 1
    theStatus = "Active"
    statusmain = 1;
  except Exception as e: 
     print(e)
     theStatus = "F: DE_portB_socket, Exception " + str(e)
#
  print("List of DE configuration ports:", DE_IP_portC)
  send_configuration()


# ringbuffer setup
  ringbufferPath =    parser['settings']['ringbuffer_path']
  ringbufferMaxSize = parser['settings']['ringbuf_maxsize']
# halt any previously started ringbuffer task(s)
  rcmd = 'killall -9 drf'
  returned_value = os.system(rcmd)
  rcmd = 'drf ringbuffer -z ' + ringbufferMaxSize + ' -p 120 -v ' + ringbufferPath + ' &'
# spin off this process asynchornously (notice the & at the end)
  returned_value = os.system(rcmd)
  print("F: ringbuffer control activated")
# start heartbeat thread that pings mainctl at intervals
 #  thread1 = hbThread(1, "pingThread-1",1)
 #  thread1.start()
  return redirect('/')

@app.route("/datarates")
def datarates():
  global theStatus
  print("Request datarates")
  send_to_mainctl(DATARATE_INQUIRY,0.1)
#  print("after check status once, theStatus=",theStatus)
  return redirect('/')

@app.route("/chkstat")
def chkstat():
   global theStatus, theDatastatus
#   print("Checking status...")
#   theStatus = check_status_once();
   print("Sending channel req")
   channel_request()
   return redirect('/')
   
def cleanup(inputstring):
  print("input string='" + inputstring + "'")
  inputstring = inputstring.replace('"','')
  inputstring = inputstring.replace("'","")
  inputstring = inputstring.replace(" ","_")
  print("cleaned input string='" + inputstring + "'")
  return(inputstring)


@app.route("/config",methods=['POST','GET'])
def config():
   global theStatus, theDataStatus
   form = MainControlForm()
   parser = configparser.ConfigParser(allow_no_value=True)
   pageStatus = "Changes do not take effect until you click Save."
   parser.read('config.ini')
   result = request.form
   if request.method == 'POST' and result.get('csubmit') != "Discard Changes" :
     statusCheck = True
     pageStatus = ""
     result = request.form
     print("F: result of config post =")
     stationGrid = result.get('theGrid')
     t = (0,0)
     try:
       print("try to convert grid")
       t = locator.locator_to_latlong(stationGrid)
       print("computed loc = ",t)
     except:
       statusCheck = False
       pageStatus = "Grid is not a valid grid. "
     if(result.get('theElevation').isnumeric() == False):
       statusCheck = False
       pageStatus = pageStatus + "Elevation must be numeric. "
       
     if(statusCheck == True):
       parser.set('profile', 'token_value', result.get('theToken'))
       parser.set('profile', 'latitude',    str(t[0]))
       parser.set('profile', 'longitude',   str(t[1]))
       parser.set('profile', 'elevation',   result.get('theElevation'))
       parser.set('profile', 'node',        result.get('theNode'))
       parser.set('profile', 'callsign',    result.get('theCall'))
       parser.set('profile', 'grid',        result.get('theGrid'))
       parser.set('profile', 'antenna0',    cleanup(result.get('antenna1')))
       parser.set('profile', 'antenna1',    cleanup(result.get('antenna2')))
       if(form.gpsdo.data == True):
         parser.set('profile','gpsdo', "Yes")
       else:
         parser.set('profile','gpsdo', "No")
       fp = open('config.ini','w')
       parser.write(fp)
       fp.close()
       pageStatus = pageStatus + "Saved."
     else:
       pageStatus = pageStatus + "NOT SAVED."

   parser.read('config.ini')
   theToken =     parser['profile']['token_value']
   theLatitude =  parser['profile']['latitude']
   theLongitude = parser['profile']['longitude']
   theElevation = parser['profile']['elevation']
   theNode =      parser['profile']['node']
   theCall =      parser['profile']['callsign']
   theGrid =      parser['profile']['grid']
   antenna1 =     parser['profile']['antenna0']
   antenna2 =     parser['profile']['antenna1']
   if(parser['profile']['gpsdo'] == "Yes"):
       form.gpsdo.data = True
   else:
       form.gpsdo.data  = False
   gpsdo =        parser['profile']['gpsdo']
   print("F: token = " + theToken)
   return render_template('profile.html', theToken = theToken,
     theLatitude = theLatitude, theLongitude = theLongitude,
     theNode = theNode, theCall = theCall, theGrid = theGrid,
     antenna1 = antenna1, antenna2 = antenna2, form=form,
     status = pageStatus, theElevation = theElevation )


@app.route("/danger", methods = ['POST','GET'])
def danger():
   global theStatus, theDataStatus
   form = MainControlForm()
   
   parser = configparser.ConfigParser(allow_no_value=True)
   parser.read('config.ini')
   if request.method == 'POST':
     result = request.form
     print("subdircadence = " + result.get('subdircadence'))
     parser.set('settings', 'subdir_cadence'       , result.get('subdircadence'))
     parser.set('settings', 'drf_compression'      , result.get('drfcompression'))
     parser.set('settings', 'milliseconds_per_file', result.get('msecperfile'))
     parser.set('settings', 'discoveryport'        , result.get('DEdiscoveryport'))
     parser.set('settings', 'configport0'          , result.get('configport0'))
     parser.set('settings', 'configport1'          , result.get('configport1'))
     parser.set('settings', 'configport2'          , result.get('configport2'))
     
     parser.set('settings', 'dataport0'          , result.get('dataport0'))
     parser.set('settings', 'dataport1'          , result.get('dataport1'))
     parser.set('settings', 'dataport2'          , result.get('dataport2'))
     
     parser.set('settings', 'antenna0',     result.get('antenna1'))
     parser.set('settings', 'antenna1',     result.get('antenna2'))
     
     fp = open('config.ini','w')
     parser.write(fp)
     fp.close()

   parser.read('config.ini')
   subdircadence =    parser['settings']['subdir_cadence']
   drfcompression =   parser['settings']['drf_compression']
   msecperfile =      parser['settings']['milliseconds_per_file']
   DEdiscoveryport =  parser['settings']['discoveryport']
   configport0 =      parser['settings']['configport0']
   configport1 =      parser['settings']['configport1']
   configport2 =      parser['settings']['configport2']
   dataport0 =        parser['settings']['dataport0']
   dataport1 =        parser['settings']['dataport1']
   dataport2 =        parser['settings']['dataport2']

   return render_template('danger.html', form = form ,
     subdircadence = subdircadence,
     drfcompression = drfcompression, msecperfile = msecperfile,
     DEdiscoveryport = DEdiscoveryport , configport0 = configport0,
     configport1 = configport1 , configport2 = configport2 ,
     dataport0 = dataport0 , dataport1 = dataport1,  
     dataport2 = dataport2 
     )

   
  # return render_template('danger.html', form=form )

@app.route("/channelantennasetup", methods = ['POST','GET'])
def channelantennasetup():
   global theStatus, theDataStatus
   return render_template('channelantennasetup.html')


@app.route("/desetup",methods=['POST','GET'])
def desetup():
   global theStatus, theDataStatus, dataCollStatus
   global statusFT8, statusWSPR, statusRG, statusSnap, statusFHR
   print("hit desetup2; request.method=",request.method)
   pageStatus = "Changes do not take effect until you click Save."
   parser = configparser.ConfigParser(allow_no_value=True)
   parser.read('config.ini')
   ringbufferPath = parser['settings']['ringbuffer_path']
   maxringbufsize = parser['settings']['ringbuf_maxsize']
   fftoutputpath  = parser['settings']['fftoutput_path']
   firehosepath   = parser['settings']['firehoser_path']
   temppath       = parser['settings']['temp_path']
   dataCollStatus = int(parser['settings']['datacollstatus'])
   
   result = request.form

   if request.method == 'GET' or result.get('csubmit') == "Discard Changes":
    channellistform = ChannelListForm()
# populate channel settings from config file
    channelcount = parser['channels']['numChannels']
    form = ChannelControlForm()
    form.channelcount.data = channelcount
    print("form maxringbufsize=",form.maxRingbufsize.data)
    print("Max ringbuf size=", maxringbufsize)
    form.maxRingbufsize.data = maxringbufsize
    print("form maxringbufsize=",form.maxRingbufsize.data)
    rate_list = []
# populate rate capabilities from config file.
# The config file should have been updated from DE sample rate list buffer.
    numRates = parser['datarates']['numRates']
    for r in range(int(numRates)):
      theRate = parser['datarates']['r'+str(r)]
      theTuple = [ str(theRate), int(theRate) ]
      rate_list.append(theTuple)

    form.channelrate.choices = rate_list
    rate1 = int(parser['channels']['datarate'])
 #   print("rate1 type = ",type(rate1))
    form.channelrate.data = rate1

    for ch in range(int(channelcount)):
      channelform = ChannelForm()
      channelform.channel_ant  = parser['channels']['p' + str(ch)] 
      channelform.channel_freq = parser['channels']['f' + str(ch)]
      channellistform.channels.append_entry(channelform)
    print("form maxringbufsize=",form.maxRingbufsize.data)
    return render_template('desetup.html',
	  ringbufferPath = ringbufferPath, channelcount = channelcount,
      channellistform = channellistform, fftoutputpath = fftoutputpath,
      firehosepath = firehosepath, temppath = temppath,
      form = form, status = pageStatus)

# if we arrive here, user has hit one of the buttons on page

  # result = request.form  (redundant)

   print("F: result=", result.get('csubmit'))

# If we reach this point, it is a POST.
# did user hit the Set channel count button?

   if result.get('csubmit') == "Set no. of channels":
     channelcount = result.get('channelcount')
     print("set #channels to ",channelcount)
     channellistform = ChannelListForm()
     form = ChannelControlForm()
     form.channelcount.data = channelcount
     rate_list = []
     numRates = parser['datarates']['numRates']
     for r in range(int(numRates)):
      theRate = parser['datarates']['r'+str(r)]
      theTuple = [ str(theRate), int(theRate) ]
      rate_list.append(theTuple)
     form.channelrate.choices = rate_list
     rate1 = int(parser['channels']['datarate'])
     form.channelrate.data = rate1
     form.maxRingbufsize.data = maxringbufsize
     for ch in range(int(channelcount)):
  #    print("add channel ",ch)
      channelform = ChannelForm()
      channelform.channel_ant  = parser['channels']['p' + str(ch)] 
      channelform.channel_freq = parser['channels']['f' + str(ch)]
      channellistform.channels.append_entry(channelform)
     print("return to desetup")
     return render_template('desetup.html',
	  ringbufferPath = ringbufferPath, channelcount = channelcount,
      channellistform = channellistform, fftoutputpath = fftoutputpath,
      firehosepath = firehosepath, temppath = temppath,
      form = form, status = pageStatus)

# user wants to save changes; update configuration file

# The range validation is done in code here due to problems with the
# WTForms range validator inside a FieldList

   if result.get('csubmit') == "Save Changes":
     statusCheck = True
  #   theStatus = "ERROR-"
     pageStatus = ""
     channelcount = result.get('channelcount')
     channelrate = result.get('channelrate')
     maxringbufsize = result.get('maxRingbufsize')
     print("Set maxringbuf size to", maxringbufsize)
     parser.set('settings','ringbuf_maxsize',maxringbufsize)
     print("set data rate to ", channelrate)
     parser.set('channels','datarate',channelrate)

     print("set #channels to ",channelcount)
     parser.set('channels','numChannels',channelcount)
     print("RESULT: ", result) 

     rgPathExists    = os.path.isdir(result.get('ringbufferPath'))
     fftPathExists   = os.path.isdir(result.get('fftoutputpath'))
     fhosePathExists = os.path.isdir(result.get('firehosepath'))
     tempPathExists   = os.path.isdir(result.get('temppath'))
     print("RG path / directory existence check: ", rgPathExists)
     if (statusRG == 1 or statusFHR == 1 or statusSnap == 1 ):
       dataCollStatus = 1

     if rgPathExists == False:
      pageStatus = "Ringbuffer path invalid or not a directory. "
      statusCheck = False
      
     print("FFT path / directory existence check: ", fftPathExists)
     if fftPathExists == False:
      pageStatus = pageStatus + "FFT output path not a directory. "
      statusCheck = False 
      
     print("firehose path / directory existence check: ", fhosePathExists)
     if fhosePathExists == False:
      pageStatus = pageStatus + "firehose output path not a directory. "
      statusCheck = False 
      
     print("temp path / directory existence check: ", tempPathExists)
     if tempPathExists == False:
      pageStatus = pageStatus + "temp output path not a directory. "
      statusCheck = False 
      
     if dataCollStatus == 1:
      pageStatus = pageStatus + "ERROR: you must stop data collection before saving changes here. "
      statusCheck = False

# save channel config to config file
     for ch in range(int(channelcount)):
       p = 'channels-' + str(ch) + '-channel_ant'
       parser.set('channels','p' + str(ch), result.get(p))
       print("p = ",p)
       print("channel #",ch," ant:",result.get(p))
       f = 'channels-' + str(ch) + '-channel_freq'
       fstr = result.get(f)
       if(is_numeric(fstr)):
         fval = float(fstr)
         if(fval < 0.1 or fval > 54.0):
           pageStatus = pageStatus +  "Freq for channel "+ str(ch) + " out of range. "
           statusCheck = False
         else:
          parser.set('channels','f' + str(ch), result.get(f))
       else:
         pageStatus = pageStatus + "Freq for channel " + str(ch) + " must be numeric."
         statusCheck = False
  
     if(statusCheck == True):
       print("Save config; ringbuffer_path=" +   result.get('ringbufferPath'))
       parser.set('settings', 'ringbuffer_path', result.get('ringbufferPath'))
       parser.set('settings', 'fftoutputpath',   result.get('fftoutputpath'))
       parser.set('settings', 'firehoser_path' , result.get('firehosepath'))
       parser.set('settings', 'temp_path',       result.get('temppath'))
       fp = open('config.ini','w')
       parser.write(fp)
       fp.close()
   
     channellistform = ChannelListForm()
     channelcount = parser['channels']['numChannels']
     form = ChannelControlForm()
     form.channelcount.data = channelcount
     rate_list = []
     numRates = parser['datarates']['numRates']
     for r in range(int(numRates)):
      theRate = parser['datarates']['r'+str(r)]
      theTuple = [ str(theRate), int(theRate) ]
      rate_list.append(theTuple)
     form.channelrate.choices = rate_list
     print("set channelrate to ", parser['channels']['datarate'])
     rate1 = int( parser['channels']['datarate'])
     form.channelrate.data = rate1
     rate_list = []
     numRates = parser['datarates']['numRates']
     for r in range(int(numRates)):
      theRate = parser['datarates']['r'+str(r)]
      theTuple = [ str(theRate), int(theRate) ]
      rate_list.append(theTuple)
     form.channelrate.choices = rate_list

 #    configCmd = CONFIG_CHANNELS + "," + channelcount + "," + parser['channels']['datarate'] + ","

     for ch in range(int(channelcount)):
  #    print("add channel ",ch)
      channelform = ChannelForm()
      channelform.channel_ant  = parser['channels']['p' + str(ch)] 
  #    configCmd = configCmd + str(ch) + "," + parser['channels']['p' + str(ch)] + ","
      channelform.channel_freq = parser['channels']['f' + str(ch)]
  #    configCmd = configCmd + parser['channels']['f' + str(ch)] + ","
      channellistform.channels.append_entry(channelform)
 #    send_to_mainctl(configCmd,1);
     if(statusCheck == True):
        send_configuration()
        pageStatus = "Setup saved."
     else:
        pageStatus = pageStatus + " NOT SAVED"

   print("return to desetup")
   return render_template('desetup.html',
	  ringbufferPath = ringbufferPath, channelcount = channelcount,
      channellistform = channellistform, fftoutputpath = fftoutputpath,
      firehosepath = firehosepath, temppath = temppath,
      form = form, status = pageStatus)

@app.route("/uploading", methods = ['POST','GET'])
def uploading():
   global theStatus, theDataStatus
   pageStatus = "Changes do not take effect until you click Save."
   form = ThrottleControlForm()
   result = request.form
   parser = configparser.ConfigParser(allow_no_value=True)
   parser.read('config.ini')
   if request.method == 'GET' or result.get('csubmit') == "Discard Changes" :
     form.throttle.data = parser['settings']['throttle']
     centralURL =     parser['settings']['central_host']
     centralPort =    parser['settings']['central_port']
     throttle =       parser['settings']['throttle']
     return render_template('uploading.html', throttle = throttle, centralURL = centralURL,
	  centralPort = centralPort, form = form, status = pageStatus)

   statusCheck = True
   if request.method == 'POST':
     
     if result.get('centralPort').isnumeric() == False :
       pageStatus = "Central port setting must be numeric. "
       statusCheck = False
       
     if statusCheck == True:
       parser.set('settings', 'throttle', result.get('throttle'))
       parser.set('settings', 'central_host', result.get('centralURL'))
       parser.set('settings', 'central_port', result.get('centralPort'))
       fp = open('config.ini','w')
       parser.write(fp)
       fp.close()
       pageStatus = "Saved."
     else:
       pageStatus = pageStatus + "NOT SAVED."
   form.throttle.data = parser['settings']['throttle']
   centralURL =     parser['settings']['central_host']
   centralPort =    parser['settings']['central_port']
   throttle =       parser['settings']['throttle']
   return render_template('uploading.html', throttle = throttle, centralURL = centralURL,
	  centralPort = centralPort, form = form, status = pageStatus)

@app.route("/callsign", methods = ['POST','GET'])
def callsign():
   global theStatus, theDataStatus
   form = CallsignForm()
   parser = configparser.ConfigParser(allow_no_value=True)
   parser.read('config.ini')
   pageStatus = "Changes do not take effect until you click Save."
   if request.method == 'GET':
     c0 = parser['monitor']['c0']
     c1 = parser['monitor']['c1']
     c2 = parser['monitor']['c2']
     c3 = parser['monitor']['c3']
     c4 = parser['monitor']['c4']
     c5 = parser['monitor']['c5']
     g0 = parser['monitor']['g0']
     g1 = parser['monitor']['g1']
     g2 = parser['monitor']['g2']
     g3 = parser['monitor']['g3']
     g4 = parser['monitor']['g4']
     g5 = parser['monitor']['g5']
     return render_template('callsign.html', form = form,
      status = pageStatus,
      c0 = c0, c1 = c1, c2 = c2, c3 = c3, c4 = c4, c5 = c5,
	  g0 = g0, g1 = g1, g2 = g2, g3 = g3, g4 = g4, g5 = g5)
	  
   if request.method == 'POST':
     result = request.form
     pageStatus = ""
     statusCheck = True
     print("F: result=", result.get('csubmit'))
     if result.get('csubmit') == "Discard Changes":
       print("F: CANCEL")
     else:
#print("F: result of callsign post =")
       for count in range(0,5):
         testgrid = result.get('g'+str(count))
     #    print("grid check 0 ",count,testgrid, len(testgrid))
         if(len(testgrid) > 0 and testgrid != "None"):  # user has entered something here
      #     print("now try it")
           try:
         #    print("grid check ",count,testgrid)
             t = (0,0)
             t = locator.locator_to_latlong(testgrid)
          #   print("locator output = ",t)
           except:
             pageStatus = pageStatus + "Grid # " + str(count) + " not a valid grid square. "
             statusCheck = False
       
      
     if(statusCheck == True):
       pageStatus = "Saved."
       parser.set('monitor', 'c0', result.get('c0'))
       parser.set('monitor', 'c1', result.get('c1'))
       parser.set('monitor', 'c2', result.get('c2'))
       parser.set('monitor', 'c3', result.get('c3'))
       parser.set('monitor', 'c4', result.get('c4'))
       parser.set('monitor', 'c5', result.get('c5'))
       parser.set('monitor', 'g0', result.get('g0'))
       parser.set('monitor', 'g1', result.get('g1'))
       parser.set('monitor', 'g2', result.get('g2'))
       parser.set('monitor', 'g3', result.get('g3'))
       parser.set('monitor', 'g4', result.get('g4'))
       parser.set('monitor', 'g5', result.get('g5'))
       fp = open('config.ini','w')
       parser.write(fp)

     c0 = parser['monitor']['c0']
     c1 = parser['monitor']['c1']
     c2 = parser['monitor']['c2']
     c3 = parser['monitor']['c3']
     c4 = parser['monitor']['c4']
     c5 = parser['monitor']['c5']
     g0 = parser['monitor']['g0']
     g1 = parser['monitor']['g1']
     g2 = parser['monitor']['g2']
     g3 = parser['monitor']['g3']
     g4 = parser['monitor']['g4']
     g5 = parser['monitor']['g5']
     
     return render_template('callsign.html', form = form,
      status = pageStatus,
      g0 = g0, g1 = g1, g2 = g2, g3 = g3, g4 = g4, g5 = g5,
	  c0 = c0, c1 = c1, c2 = c2, c3 = c3, c4 = c4, c5 = c5)

@app.route("/notification", methods = ['POST','GET'])
def notification():
   form = ServerControlForm()
   parser = configparser.ConfigParser(allow_no_value=True)
   parser.read('config.ini')
   theStatus = ""
   if request.method == 'GET':
     print("F: smtpsvr = ", parser['email']['smtpsvr'])
     smtpsvr =     parser['email']['smtpsvr']
     emailfrom=    parser['email']['emailfrom']
     emailto =     parser['email']['emailto']
     smtpport =    parser['email']['smtpport']
     smtptimeout = parser['email']['smtptimeout']
     smtpuid =     parser['email']['smtpuid']
     smtppw =      parser['email']['smtppw']
     return render_template('notification.html',
	  smtpsvr = smtpsvr, emailfrom = emailfrom,
      emailto = emailto, smtpport = smtpport,
      smtptimeout = smtptimeout, smtpuid = smtpuid,
      smtppw = smtppw, status = theStatus, form = form)

   form = ServerControlForm()
   if not form.validate():
     result = request.form
     emailto = result.get('emailto')
     smtpsvr = result.get('smtpsvr')
     emailfrom = result.get('emailfrom')
     smtpport = result.get('smtpport')
     smtptimeout = result.get('smtptimeout')
     smtppw = result.get('smtppw')
     smtpuid = result.get('smtpuid')
     print("email to="+emailto)
     print("smtpsvr="+smtpsvr)
     theStatus = form.errors

     result = request.form   

     return render_template('notification.html',
	  smtpsvr = smtpsvr, emailfrom = emailfrom,
     emailto = emailto, smtpport = smtpport,
      smtptimeout = smtptimeout, smtpuid = smtpuid,
      smtppw = smtppw, status = theStatus, form=form)

   if request.method == 'POST':
     result = request.form
     print("F: result=", result.get('csubmit'))
     if result.get('csubmit') == "Discard Changes":
       print("F: CANCEL")
     elif result.get('csubmit') == "Send test email" :
        print("Send test email")
        try:
          msg = MIMEMultipart()
          smtpsvr =     parser['email']['smtpsvr']
          msg['From'] = parser['email']['emailfrom']
          msg['To'] =   parser['email']['emailto']
          msg['Subject'] = "Test message from your TangerineSDR"
          smtpport =    parser['email']['smtpport']
          smtptimeout = parser['email']['smtptimeout']
          smtpuid =     parser['email']['smtpuid']
          smtppw =      parser['email']['smtppw']
          body = "Test message from your TangerineSDR"
          msg.attach(MIMEText(body,'plain'))
          server = smtplib.SMTP(smtpsvr,smtpport,'None',int(smtptimeout))
          server.ehlo()
          server.starttls()
          server.login(smtpuid,smtppw)
          text = msg.as_string()
          server.sendmail(parser['email']['emailfrom'],parser['email']['emailto'],text)
          print("sendmail done")
          theStatus = "Test mail sent."
        except Exception as e: 
         print(e)
         theStatus = e
        
     else:
        print("F: reached POST on notification;", result.get('smtpsvr'))
        parser.set('email', 'smtpsvr', result.get('smtpsvr'))
        parser.set('email', 'emailfrom', result.get('emailfrom'))
        parser.set('email', 'emailto', result.get('emailto'))
        parser.set('email', 'smtpport', result.get('smtpport'))
        parser.set('email', 'smtptimeout', result.get('smtptimeout'))
        parser.set('email', 'smtpuid', result.get('smtpuid'))
        parser.set('email', 'smtppw', result.get('smtppw'))
        fp = open('config.ini','w')
        parser.write(fp)

     smtpsvr =     parser['email']['smtpsvr']
     emailfrom=    parser['email']['emailfrom']
     emailto =     parser['email']['emailto']
     smtpport =    parser['email']['smtpport']
     smtptimeout = parser['email']['smtptimeout']
     smtpuid =     parser['email']['smtpuid']
     smtppw =      parser['email']['smtppw']
     return render_template('notification.html',
	  smtpsvr = smtpsvr, emailfrom = emailfrom,
      emailto = emailto, smtpport = smtpport,
      smtptimeout = smtptimeout, smtpuid = smtpuid,
      smtppw = smtppw, status = theStatus)


# configuration of FT8 subchannels
@app.route("/propagation",methods=['POST','GET'])
def propagation():   
   global theStatus, theDataStatus
   global statusFT8, statusWSPR, statusRG, statusSnap, statusFHR
   form = ChannelControlForm()
   parser = configparser.ConfigParser(allow_no_value=True)
   parser.read('config.ini')
   psk = False
   if(statusFT8 == 1 or statusWSPR == 1):
     form.status = "Propagation monitoring is active"
   if request.method == 'GET':
     form.antennaport0.data =     parser['settings']['ftant0']
     form.antennaport1.data =     parser['settings']['ftant1']
     form.antennaport2.data =     parser['settings']['ftant2']
     form.antennaport3.data =     parser['settings']['ftant3']
     form.antennaport4.data =     parser['settings']['ftant4']
     form.antennaport5.data =     parser['settings']['ftant5']
     form.antennaport6.data =     parser['settings']['ftant6']
     form.antennaport7.data =     parser['settings']['ftant7']
     form.ft80f.data        =     parser['settings']['ft80f'] 
     form.ft81f.data        =     parser['settings']['ft81f'] 
     form.ft82f.data        =     parser['settings']['ft82f']
     form.ft83f.data        =     parser['settings']['ft83f']
     form.ft84f.data        =     parser['settings']['ft84f']
     form.ft85f.data        =     parser['settings']['ft85f']
     form.ft86f.data        =     parser['settings']['ft86f']
     form.ft87f.data        =     parser['settings']['ft87f']
     if(parser['settings']['psk_upload'] == "On"):
       psk = True
       form.pskindicator.data = True
       print("detected psk = On")
     else:
       psk = False
       print("detected psk=Off")
       
     return render_template('ft8setup.html',
  #    pskindicator = psk,
      form  = form
      )

   if request.method == 'POST':
     result = request.form
     print("F: result=", result.get('csubmit'))
     if result.get('csubmit') == "Discard Changes":
       print("F: CANCEL")
     else:
       print("F: POST ringbufferPath =", result.get('ringbufferPath'))
       if(statusFT8 == 1 or statusWSPR == 1):
         form.status = "ERROR. Stop FT8/WSPR before changing these settings."
         return render_template('ft8setup.html', form = form)
       parser.set('settings', 'ftant0',            form.antennaport0.data)
       parser.set('settings', 'ft80f',             form.ft80f.data)
       parser.set('settings', 'ftant1',            form.antennaport1.data)
       parser.set('settings', 'ft81f',             form.ft81f.data)
       parser.set('settings', 'ftant2',            form.antennaport2.data)
       parser.set('settings', 'ft82f',             form.ft82f.data)
       parser.set('settings', 'ftant3',            form.antennaport3.data)
       parser.set('settings', 'ft83f',             form.ft83f.data)
       parser.set('settings', 'ftant4',            form.antennaport4.data)
       parser.set('settings', 'ft84f',             form.ft84f.data)
       parser.set('settings', 'ftant5',            form.antennaport5.data)
       parser.set('settings', 'ft85f',             form.ft85f.data)
       parser.set('settings', 'ftant6',            form.antennaport6.data)
       parser.set('settings', 'ft86f',             form.ft86f.data)
       parser.set('settings', 'ftant7',            form.antennaport7.data)
       parser.set('settings', 'ft87f',             form.ft87f.data)  
       if(form.pskindicator.data == True):
         parser.set('settings','psk_upload', "On")
       else:
         parser.set('settings','psk_upload', "Off")
       fp = open('config.ini','w')
       parser.write(fp)
       fp.close()
     ringbufferPath = parser['settings']['ringbuffer_path']
     form.antennaport0.data =     parser['settings']['ftant0']
     form.antennaport1.data =     parser['settings']['ftant1']
     form.antennaport2.data =     parser['settings']['ftant2']
     form.antennaport3.data =     parser['settings']['ftant3']
     form.antennaport4.data =     parser['settings']['ftant4']
     form.antennaport5.data =     parser['settings']['ftant5']
     form.antennaport6.data =     parser['settings']['ftant6']
     form.antennaport7.data =     parser['settings']['ftant7']
     ft80f =     parser['settings']['ft80f']
     ft81f =     parser['settings']['ft81f']
     ft82f =     parser['settings']['ft82f']
     ft83f =     parser['settings']['ft83f']
     ft84f =     parser['settings']['ft84f']
     ft85f =     parser['settings']['ft85f']
     ft86f =     parser['settings']['ft86f']
     ft87f =     parser['settings']['ft87f']
     if(parser['settings']['psk_upload'] == "On"):
       form.pskindicator.data = True
     else:
       form.pskindicator.data = False
     return render_template('ft8setup.html',
      form = form
      )

# configure WSPR settings
@app.route("/propagation2",methods=['POST','GET'])
def propagation2():
   global theStatus, theDataStatus
   global statusFT8, statusWSPR, statusRG, statusSnap, statusFHR
   form = ChannelControlForm()
   parser = configparser.ConfigParser(allow_no_value=True)
   parser.read('config.ini')
   psk = False
   if(statusFT8 == 1 or statusWSPR == 1):
     form.status = "Propagation monitoring is active"
   if request.method == 'GET':
     form.antennaport0.data =     parser['settings']['wsant0']
     form.antennaport1.data =     parser['settings']['wsant1']
     form.antennaport2.data =     parser['settings']['wsant2']
     form.antennaport3.data =     parser['settings']['wsant3']
     form.antennaport4.data =     parser['settings']['wsant4']
     form.antennaport5.data =     parser['settings']['wsant5']
     form.antennaport6.data =     parser['settings']['wsant6']
     form.antennaport7.data =     parser['settings']['wsant7']
     form.ws0f.data         =     parser['settings']['ws0f'] 
     form.ws1f.data         =     parser['settings']['ws1f'] 
     form.ws2f.data         =     parser['settings']['ws2f']
     form.ws3f.data         =     parser['settings']['ws3f']
     form.ws4f.data         =     parser['settings']['ws4f']
     form.ws5f.data         =     parser['settings']['ws5f']
     form.ws6f.data         =     parser['settings']['ws6f']
     form.ws7f.data         =     parser['settings']['ws7f']
     if(parser['settings']['wspr_upload'] == "On"):
       wspr = True
       form.wsprindicator.data = True
       print("F: user set upload wspr = On")
     else:
       wspr = False
       form.wsprindicator.data = False
       print("user set upload wspr=Off")
       
     return render_template('wsprsetup.html',
  #    pskindicator = psk,
      form  = form
      )

   if request.method == 'POST':
     result = request.form
     print("F: result=", result.get('csubmit'))
     if result.get('csubmit') == "Discard Changes":
       print("F: CANCEL")
     else:
       if(statusFT8 == 1 or statusWSPR == 1):
         form.status = "ERROR. Stop FT8/WSPR before changing these settings."
         return render_template('wsprsetup.html', form = form)
       parser.set('settings', 'wsant0',            form.antennaport0.data)
       parser.set('settings', 'ws0f',              form.ws0f.data)
       parser.set('settings', 'wsant1',            form.antennaport1.data)
       parser.set('settings', 'ws1f',              form.ws1f.data)
       parser.set('settings', 'wsant2',            form.antennaport2.data)
       parser.set('settings', 'ws2f',              form.ws2f.data)
       parser.set('settings', 'wsant3',            form.antennaport3.data)
       parser.set('settings', 'ws3f',              form.ws3f.data)
       parser.set('settings', 'wsant4',            form.antennaport4.data)
       parser.set('settings', 'ws4f',              form.ws4f.data)
       parser.set('settings', 'wsant5',            form.antennaport5.data)
       parser.set('settings', 'ws5f',              form.ws5f.data)
       parser.set('settings', 'wsant6',            form.antennaport6.data)
       parser.set('settings', 'ws6f',              form.ws6f.data)
       parser.set('settings', 'wsant7',            form.antennaport7.data)
       parser.set('settings', 'ws7f',              form.ws7f.data)   
       if(form.wsprindicator.data == True):
         parser.set('settings','wspr_upload', "On")
       else:
         parser.set('settings','wspr_upload', "Off")
       fp = open('config.ini','w')
       parser.write(fp)
       fp.close()

     form.antennaport0.data =     parser['settings']['wsant0']
     form.antennaport1.data =     parser['settings']['wsant1']
     form.antennaport2.data =     parser['settings']['wsant2']
     form.antennaport3.data =     parser['settings']['wsant3']
     form.antennaport4.data =     parser['settings']['wsant4']
     form.antennaport5.data =     parser['settings']['wsant5']
     form.antennaport6.data =     parser['settings']['wsant6']
     form.antennaport7.data =     parser['settings']['wsant7']
     ws0f =     parser['settings']['ws0f']
     ws1f =     parser['settings']['ws1f']
     ws2f =     parser['settings']['ws2f']
     ws3f =     parser['settings']['ws3f']
     ws4f =     parser['settings']['ws4f']
     ws5f =     parser['settings']['ws5f']
     ws6f =     parser['settings']['ws6f']
     ws7f =     parser['settings']['ws7f']
     if(parser['settings']['wspr_upload'] == "On"):
       form.wsprindicator.data = True
     else:
       form.wsprindicator.data = False
     return render_template('wsprsetup.html',
      form = form
      )


# The following is called by a java script in tangerine.html for showing the
# most recent number of FT8 spots by band

@app.route('/_ft8list')
def ft8list():
# print("ft8list")
  ft8string = ""
  band = []
 # print("Entering _/ft8list")
  parser = configparser.ConfigParser(allow_no_value=True)
  parser.read('config.ini')
  for i in range(7):
    ia = "ft8" + str(i) + "f"
    ib = "ftant" + str(i)
    if(parser['settings'][ib] != "Off"):
      band.append(parser['settings'][ia])
    #  print("ft8 band list=" + band[i])

  try:
    plist = []
    for fno in range(len(band)):

 #    fname = '/mnt/RAM_disk/FT8/decoded' + str(fno) +'.txt'
     fname = parser['settings']['ramdisk_path'] + "/FT8/decoded"  + str(fno) +'.txt'
    # print("checking file",fname)
     dm = time.ctime(os.path.getmtime(fname))
   #  dm = "d"
     f = open(fname,"r")
   #  print("file opened")
   #  print("ft8list" + str(len(f.readlines())) )
    # print("ft8 readlines")
     plist.append(len(f.readlines()))
    # print("append done")
    # print(plist)
     f.close()
      
# here we build a JSON string to populate the FT8 panel
    ft8string = '{'
    ft8string = ft8string + '"0":"MHz  spots ' + dm + '",'
 #   print('ft8str',ft8string)
    for i in range(len(band)):
     pval = str(plist[i])
     ft8string = ft8string + '"' + str(i+1) + '":"' +  \
       str(band[i]) + ' - ' + pval + ' ",'

    ft8string = ft8string + '"end":" "}'
   # print("ft8string= " , ft8string)
  except Exception as ex:
   # print("F: exception trying to build JSON FT8 list")
  #  print(ex)
# no-op
    z=1

  return Response(ft8string, mimetype='application/json')

######################################################################
@app.errorhandler(404)
def page_not_found(e):
    return render_template("notfound.html")


if __name__ == "__main__":
#	app.run(host='0.0.0.0')
#	app.run(debug = True)

	from waitress import serve
	serve(app, host = "0.0.0.0", port=5000) 
#	serve(app)
#	serve(app, host = "192.168.1.75", port=5000)


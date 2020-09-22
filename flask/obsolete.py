
def send_to_mainctl(cmdToSend,waitTime):
  global theStatus, rateList, tcp_client
  print("F: sending:'" + cmdToSend +"'")

  data = cmdToSend                 # + "\n"  
  try:
     print("F: send cmd:",cmdToSend)
     tcp_client.sendall(data.encode())
     print("F: wait for DE response")
     if(waitTime > 0):
       time.sleep(waitTime)
     print("F: try to receive response")
     received = "NO RESPONSE"
    # Read data from the TCP server and close the connection
     try:
       received = tcp_client.recv(1024, socket.MSG_DONTWAIT)
 #      print("F: received data from DE: ", received)
       d = received.decode()
     #  print("F: decoded:",d)
       print("F: buftype is '",received[0:2],"'")
       print("F: bytes=",received[0],"/",received[1],"/",received[2])
       theStatus = "Active"
       statusmain = 1
#       print("find:",received[0:2].find("DR"))
       if(d.find("DR") !=  -1):
         print("F: DR buffer received")
         parser = configparser.ConfigParser(allow_no_value=True)
         parser.read('config.ini')
         rateList = []
         a = d.split(":")
         b = a[1].split(";")
       
         print("b=",b)
         rateCount = 0
         for ratepair in b:
           c = ratepair.split(',')
           lenc = len(c[0])
           print("c[0]=",c[0]," len c[0]=",lenc)

           if(lenc > 3):
             break
           rateList.append(c)
           parser.set('datarates', 'r'+str(rateCount), c[1] )
           rateCount = rateCount + 1
           print("ratepair=",ratepair," c=",c, "c[1]=",c[1])
         print("rateList = ",rateList)
         parser.set('datarates','numrates',str(rateCount))
         fp = open('config.ini','w')
         parser.write(fp)
         fp.close()
     except Exception as e:
       print("F: exception on recv,")    # , e.message)
       theStatus = "Mainctl stopped or DE disconnected , error: " + str(e)
     theStatus = "Active"
     print("F: mainctl answered ", received, " thestatus = ",theStatus)

  except Exception as e: 
     print(e)
     theStatus = "F: send command to mainctl, Exception " + str(e)
  finally:
     print("F: bypassing TCP close")
   #  print("F: close connection to mainctl")
   #  tcp_client.close()

def channel_request():
  print("  * * * * * Send channel creation request * * * *")   
  parser = configparser.ConfigParser(allow_no_value=True)
  parser.read('config.ini')
# ports that mainctl will listen on for traffic from DE
  configPort =  parser['settings']['controlport']
  dataPort   =  parser['settings']['dataport']
# commas must separate fields for token processing to work in mainctl
  send_to_mainctl((CREATE_CHANNEL + "," + "0 ," + configPort + "," + dataPort),1 )
  
def check_status_once():
  global theStatus
  send_to_mainctl(STATUS_INQUIRY,4)
  print("after check status once, theStatus=",theStatus)
  return

def ping_mainctl():
  while(1):
    time.sleep(60)
    localtime = time.asctime(time.localtime(time.time()))
    print("F: PING mainctl with S? at ", localtime)
    send_to_mainctl("S?",1)
    print("F: mainctl replied") 



def send_channel_config():  # send channel configuration command to DE
  global theStatus
  parser = configparser.ConfigParser(allow_no_value=True)
  parser.read('config.ini')
  channelcount = parser['channels']['numChannels']
  rate_list = []
  numRates = parser['datarates']['numRates']
# this is channel zero (RG-type data)
  configCmd = CONFIG_CHANNELS + ", 0, " + channelcount + "," + parser['channels']['datarate'] + ","
  for ch in range(int(channelcount)):
    print("add channel ",ch)
    configCmd = configCmd + str(ch) + "," + parser['channels']['p' + str(ch)] + ","
    configCmd = configCmd + parser['channels']['f' + str(ch)] + ","
  print("Sending CH config command to DE")

  send_to_mainctl(configCmd,1);
  return



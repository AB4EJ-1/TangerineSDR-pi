/* Copyright (C) 2019 The University of Alabama
* Author: William (Bill) Engelke, AB4EJ
* With funding from the Center for Advanced Public Safety and
* The National Science Foundation.
*
* This program is free software; you can redistribute it and/or
* modify it under the terms of the GNU General Public License
* as published by the Free Software Foundation; either version 2
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place - S          sprintf(syscommand_start,"./DEmain2 %i %s %i &",(int)ntohs(server_addr.sin_port),inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

            printf("command = %s \n",syscommand_start);


          close(sock1);  // may have to re-establish this later
          system(syscommand_start);uite 330, Boston, MA  02111-1307, USA.
*
*/

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <pthread.h>
#include <math.h>
#include <stdbool.h>
#include <fcntl.h>
#include <errno.h>
#include "de_signals.h"

#include <complex.h>
#include <fftw3.h>


#define PORT 1024

#define UDPPORT 7100
#define FLEXFT_IN 7790
#define FLEXDATA_IN 7791
#define FLEXWSPR_IN 7792
#define FFT_N 48000

struct flexDataSample
  {
  float I_val;
  float Q_val;
  };

typedef struct flexDataBuf
 {
 char VITA_hdr1[2];  // rightmost 4 bits is a packet counter
 int16_t  VITA_packetsize;
 char stream_ID[4];
 char class_ID[8];
 uint32_t time_stamp;
 uint64_t fractional_seconds;
 struct flexDataSample flexDataSample[512];
 } FLEXBUF;
struct sockaddr_in flex_addr;
static  int fd;

//static struct dataBuf iqbuffer;
static struct flexDataBuf iqbuffer2;
static struct VITAdataBuf iqbuffer2_in;
static struct VITAdataBuf iqbuffer2_out;
static struct VITAdataBuf ft8buffer_out[4];
static struct VITAdataBuf wsprbuffer_out[8];

static int LH_port;
static int LH_IP;
//static char[15];
struct sockaddr_in client_addr;
struct sockaddr_in client_addr2;
struct sockaddr_in client_addr3;
struct sockaddr_in server_addr;
struct sockaddr_in config_in_addr;
struct sockaddr_in portF_addr;

int sock;

int sockft8out;
int sockwsprout;
int sock1;

int sock3;
int sock5;
int sock6;
int sock7;

//static int sock4;
long cmdthreadID;
static int CCport;
//int cmdport;
int stoplink;
int stopData;
int stopDataColl;
int stopft8;
int stopwspr;
int ft8active;
int wspractive;
int config_busy;
int noOfChannels;
int dataRate;  // rate at which activated channel runs
struct iqpair {
  float ival; 
  float qval;
};



static uint16_t LH_CONF_IN_port[3];  // port C, receives ACK or NAK from config request
static uint16_t LH_CONF_OUT_port[3]; // for sending (outbound) config request to DE
//static uint16_t DE_CONF_IN_portB;  // port B ; DE listens for CC on this port
static uint16_t LH_DATA_IN_port[3];  // port F; LH listens for spectrum data on this port
static uint16_t DE_CH_IN_port[3] = {50001,50002,50003};    // port D; DE listens channel setup on this port
static uint16_t LH_DATA_OUT_port ; // for sending (outbound) data (e.g., mic audio) to DE (unused)

static uint16_t FH_DATA_IN_port;
static char FH_DATA_IN_IP[30];
static uint16_t firehoseLmode = 0; // set to 1 when in Firehose-L mode


static  fftwf_complex FFT_data[FFT_N];
static  fftwf_plan p;

/////////////////////////////////////////////////////////////////////
void *sendFT8flex(void * threadid){
  int sock4;
  fd_set readfd;
  int count;
  int streamNo = 0;
  ft8active = 1;

// FFT_in and out the same for now
  p = fftwf_plan_dft_1d(FFT_N, FFT_data, FFT_data, FFTW_FORWARD, FFTW_ESTIMATE);


  printf("in Flex FT8 thread; init sock4\n");
  sock4 = socket(AF_INET, SOCK_DGRAM, 0);  // for receiving IQ packets from FlexRadio (FT8)

  printf("after socket assign, FT8 sock4= %i\n",sock4);
  if(sock4 < 0) {
    printf("sock4 error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
    }

  int yes = 1;  // make socket re-usable
  if(setsockopt(sock4, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes)) == -1) {
   printf("sock4: Error setting sock option SO_REUSEADDR\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
   }

  printf("sock4 created\n");
  int addr_len = sizeof(struct sockaddr_in);
  memset((void*)&flex_addr, 0, addr_len);
  flex_addr.sin_family = AF_INET;
  flex_addr.sin_addr.s_addr = htons(INADDR_ANY);
  flex_addr.sin_port = htons(FLEXFT_IN);
  printf("bind sock4\n:");
  int ret = bind(sock4, (struct sockaddr*)&flex_addr, addr_len);          


  if (ret < 0){
    printf("bind error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
     }
  FD_ZERO(&readfd);
  FD_SET(sock4, &readfd);
  printf("in flex FT8 thread read from port %i\n",FLEXFT_IN);
 // client_addr.sin_port = htons(LH_DATA_IN_port);
// temporary hard code for ft8 port testing
  client_addr2.sin_family = AF_INET;
  client_addr2.sin_addr.s_addr = client_addr.sin_addr.s_addr;
  client_addr2.sin_port = htons(LH_DATA_IN_port[1]);
 ret = 1;

// note that this clears all copies of ft8buffer_out
 memset(&ft8buffer_out,0,sizeof(ft8buffer_out));
 uint64_t samplecount = 0;  // number of IQ samples processed from input
 uint64_t totaloutputbuffercount[4];  // number of buffers sent
 uint64_t totalinputsamplecount[4];
 int outputbuffercount[4];
 for (int i = 0; i < 4; i++)
   {
   outputbuffercount[i] = 0;
   totaloutputbuffercount[i] = 0;
   totalinputsamplecount[i] = -1;  // so that first increment goes to zero
   }

 while(1==1) {  // repeating loop

   if(stopft8)
	 {
     puts("UDP thread end; close sock4");
     ft8active = 0;
     close(sock4);
	 pthread_exit(NULL);
	 }


    count = recvfrom(sock4, &iqbuffer2, sizeof(iqbuffer2),0, (struct sockaddr*)&flex_addr, &addr_len);

    streamNo = (int16_t)iqbuffer2.stream_ID[3];
 
// build ft8buffer header

   memcpy(ft8buffer_out[streamNo].VITA_hdr1, iqbuffer2.VITA_hdr1,sizeof(iqbuffer2.VITA_hdr1));
   ft8buffer_out[streamNo].stream_ID[0] = 0x46;    // F
   ft8buffer_out[streamNo].stream_ID[1] = 0x54;    // T
   ft8buffer_out[streamNo].stream_ID[2] = iqbuffer2.stream_ID[2]; // copy from input
   ft8buffer_out[streamNo].stream_ID[3] = iqbuffer2.stream_ID[3]; // copy from input
   ft8buffer_out[streamNo].VITA_packetsize = sizeof(ft8buffer_out[0]);
   ft8buffer_out[streamNo].time_stamp = (uint32_t)time(NULL);
   ft8buffer_out[streamNo].sample_count = totaloutputbuffercount[streamNo];

  for(int inputbuffercount =0; inputbuffercount < 512; inputbuffercount++)
   {
   totalinputsamplecount[streamNo]++;  // goes to zero on first buffer
   if((totalinputsamplecount[streamNo] % 12) != 0)  // crummy decimation; TODO: correct this
     continue;
  
   
   ft8buffer_out[streamNo].theDataSample[outputbuffercount[streamNo]].I_val = iqbuffer2.flexDataSample[inputbuffercount].I_val;
   ft8buffer_out[streamNo].theDataSample[outputbuffercount[streamNo]].Q_val = iqbuffer2.flexDataSample[inputbuffercount].Q_val;

    outputbuffercount[streamNo]++;

    if(outputbuffercount[streamNo] >= 1024)  // have we filled the output buffer?
     {
      printf("FT8: try to send, streamNo = %i \n",streamNo);

      int sentBytes = sendto(sockft8out, (const struct VITAdataBuf *)&ft8buffer_out[streamNo], sizeof(ft8buffer_out[0]), 0, 
	      (struct sockaddr*)&client_addr2, sizeof(client_addr2));
       outputbuffercount[streamNo] = 0;
       totaloutputbuffercount[streamNo] ++;
   //    printf("sent bytes %i\n",sentBytes);
      }

    }  // end of inputbuffercount loop (512 samples in the flex IQ packet)


  } // end of repeating loop

 }  // end of function


/////////////////////////////////////////////////////////////////////
void *sendwsprflex(void * threadid){

  struct flexDataBuf iqbuffer3;
  fd_set readfd;
  int count;
  int streamNo = 0;
  wspractive = 1;
  printf("in Flex wspr thread; init sock7\n");
  sock7 = socket(AF_INET, SOCK_DGRAM, 0);  // for receiving IQ packets from FlexRadio (for WSPR)

  printf("after wspr socket assign, wspr sock7= %i\n",sock7);
  if(sock7 < 0) {
    printf("sock7 error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
    }

  int yes = 1;  // make socket re-usable
  if(setsockopt(sock7, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes)) == -1) {
   printf("sock7: Error setting sock option SO_REUSEADDR\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
   }

  printf("sock7 created\n");
  int addr_len = sizeof(struct sockaddr_in);
  memset((void*)&flex_addr, 0, addr_len);
  flex_addr.sin_family = AF_INET;
  flex_addr.sin_addr.s_addr = htons(INADDR_ANY);
  flex_addr.sin_port = htons(FLEXWSPR_IN);
  printf("bind sock7\n:");
  int ret = bind(sock7, (struct sockaddr*)&flex_addr, addr_len);
  if (ret < 0){
    printf("bind error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
     }
  FD_ZERO(&readfd);
  FD_SET(sock7, &readfd);
  printf("in flex wspr thread read from port %i\n",FLEXWSPR_IN);
 // client_addr.sin_port = htons(LH_DATA_IN_port);
// temporary hard code for ft8 port testing
  client_addr3.sin_family = AF_INET;
  client_addr3.sin_addr.s_addr = client_addr.sin_addr.s_addr;
  client_addr3.sin_port = htons(LH_DATA_IN_port[2]);  // hard code to use Channel 2
 ret = 1;

// note that this clears all copies of ft8buffer_out
 memset(&ft8buffer_out,0,sizeof(ft8buffer_out));
 uint64_t samplecount = 0;  // number of IQ samples processed from input
 uint64_t totaloutputbuffercount[4];  // number of buffers sent
 uint64_t totalinputsamplecount[4];
 int outputbuffercount[4];
 for (int i = 0; i < 4; i++)
   {
   outputbuffercount[i] = 0;
   totaloutputbuffercount[i] = 0;
   totalinputsamplecount[i] = -1;  // so that first increment goes to zero
   }

 while(1==1) {  // repeating loop

   if(stopwspr == 1)
	 {
     puts("stopwspr flag set; UDP thread end; close sock7");
     ft8active = 0;
     close(sock7);
	 pthread_exit(NULL);
	 }


    count = recvfrom(sock7, &iqbuffer3, sizeof(iqbuffer3),0, (struct sockaddr*)&flex_addr, &addr_len);
   // printf("got %i bytes from sock7\n",count);
    streamNo = (int16_t)iqbuffer3.stream_ID[3];
 
// build wsprbuffer header

   memcpy(wsprbuffer_out[streamNo].VITA_hdr1, iqbuffer3.VITA_hdr1,sizeof(iqbuffer3.VITA_hdr1));
   wsprbuffer_out[streamNo].stream_ID[0] = 0x57;    // W
   wsprbuffer_out[streamNo].stream_ID[1] = 0x53;    // S
   wsprbuffer_out[streamNo].stream_ID[2] = iqbuffer3.stream_ID[2]; // copy from input
   wsprbuffer_out[streamNo].stream_ID[3] = iqbuffer3.stream_ID[3]; // copy from input
   wsprbuffer_out[streamNo].VITA_packetsize = sizeof(wsprbuffer_out[0]);
   wsprbuffer_out[streamNo].time_stamp = (uint32_t)time(NULL);
   wsprbuffer_out[streamNo].sample_count = totaloutputbuffercount[streamNo];

  for(int inputbuffercount =0; inputbuffercount < 512; inputbuffercount++)
   {
   totalinputsamplecount[streamNo]++;  // goes to zero on first buffer
   if((totalinputsamplecount[streamNo] % 128) != 0)  // crummy decimation; TODO: correct this
     continue;
   // inputbuffercount is multiple of 128 (or zero); save it
   
   wsprbuffer_out[streamNo].theDataSample[outputbuffercount[streamNo]].I_val = iqbuffer3.flexDataSample[inputbuffercount].I_val;
   wsprbuffer_out[streamNo].theDataSample[outputbuffercount[streamNo]].Q_val = iqbuffer3.flexDataSample[inputbuffercount].Q_val;

    outputbuffercount[streamNo]++;

    if(outputbuffercount[streamNo] >= 1024)  // have we filled the output buffer?
     {
      printf("wspr: try to send to port %i, streamNo = %i \n",LH_DATA_IN_port[2],streamNo);

      int sentBytes = sendto(sockwsprout, (const struct VITAdataBuf *)&wsprbuffer_out[streamNo], sizeof(wsprbuffer_out[0]), 0, 
	      (struct sockaddr*)&client_addr3, sizeof(client_addr3));
      printf("#bytes sent: %i\n",sentBytes);
       outputbuffercount[streamNo] = 0;
       totaloutputbuffercount[streamNo] ++;
   //    printf("sent bytes %i\n",sentBytes);
      }

    }  // end of inputbuffercount loop (512 samples in the flex IQ packet)


  } // end of repeating loop

 }  // end of function


//////////////send FlexData using Firehose-L mode  ////////////////////////////
void *sendFHData(void * threadid){
// forward IQ data from flex to local fast server in VITA-T format
  printf("Starting FIREHOSE-L thread\n");
// TODO: add 32-bit time stamp & buffer count in right place for use by LH (DRF ddata handler)
  uint64_t theSampleCount = 0;
  fd_set readfd;
  int sockRGout;
  int count;
  if((sockRGout = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)) < 0)
          {
          perror("socket");
          printf("creating sockRGout failed\n");
          }
      else
          {
          printf("sockRGout created\n");
          }
  struct sockaddr_in si_LH_portF0;  // will use sockRGout
  memset((char *) &si_LH_portF0, 0, sizeof(si_LH_portF0));
  si_LH_portF0.sin_family = AF_INET;


  si_LH_portF0.sin_addr.s_addr = inet_addr(FH_DATA_IN_IP);
  si_LH_portF0.sin_port = htons(FH_DATA_IN_port);
  

  printf("in Flex DATA thread; start to send data to Port F %i; init sock5\n",LH_DATA_IN_port[0]);
  sock5 = socket(AF_INET, SOCK_DGRAM, 0);
  printf("after socket assign, sock5= %i\n",sock5);
  if(sock5 < 0) {
    printf("sock5 error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
    }
  int yes = 1;  // make socket re-usable
  if(setsockopt(sock5, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes)) == -1) {
   printf("sock5: Error setting sock option SO_REUSEADDR\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
   }

  printf("sock5 created\n");
  int addr_len = sizeof(struct sockaddr_in);
  memset((void*)&flex_addr, 0, addr_len);
  flex_addr.sin_family = AF_INET;
  flex_addr.sin_addr.s_addr = htons(INADDR_ANY);
  flex_addr.sin_port = htons(FLEXDATA_IN);
  printf("bind sock5\n:");
  int ret = bind(sock5, (struct sockaddr*)&flex_addr, addr_len);
  if (ret < 0){
    printf("sock5 (Flex) bind error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
     }
  FD_ZERO(&readfd);
  FD_SET(sock5, &readfd);
  printf("in flex Data thread read from port %i\n",FLEXDATA_IN);
 // client_addr.sin_port = htons(LH_DATA_IN_port[0]);
 ret = 1;
 while(1==1) {  // repeating loop

   if(stopDataColl)
	 {
     puts("UDP thread end");
     ft8active = 0;
     close(sock5);
	 pthread_exit(NULL);
	 }

  if(ret > 0){
   if (FD_ISSET(sock5, &readfd)){
 //   printf("try read\n");
    count = recvfrom(sock5, &iqbuffer2_in, sizeof(iqbuffer2_in),0, (struct sockaddr*)&flex_addr, &addr_len);

    memcpy(iqbuffer2_out.VITA_hdr1, iqbuffer2_in.VITA_hdr1, sizeof(iqbuffer2_out.VITA_hdr1));

    iqbuffer2_out.VITA_packetsize = sizeof(iqbuffer2_out);
    iqbuffer2_out.stream_ID[0] = 0x52;   // put "RG" into stream ID
    iqbuffer2_out.stream_ID[1] = 0x47;
    iqbuffer2_out.stream_ID[2] = 1;   // number of embedded subchannels in buffer
    iqbuffer2_out.stream_ID[3] = iqbuffer2_in.stream_ID[3];
    iqbuffer2_out.time_stamp = (uint32_t)time(NULL);
    iqbuffer2_out.sample_count = theSampleCount;
    theSampleCount++; // this is actually a packet count, at least for now
  //  printf("timestamp = %i \n",iqbuffer2_out.time_stamp);
    for(int i=0; i < 512; i++)
     {
      iqbuffer2_out.theDataSample[i] = iqbuffer2_in.theDataSample[i];
     }

    count = recvfrom(sock5, &iqbuffer2_in, sizeof(iqbuffer2_in),0, (struct sockaddr*)&flex_addr, &addr_len);
 //   printf("bytes received = %i\n",count);

    for(int i=0; i < 512; i++)
     {
      iqbuffer2_out.theDataSample[i + 512] = iqbuffer2_in.theDataSample[i];
     }
    int slen = sizeof(si_LH_portF0);

    int sentBytes = sendto(sockRGout, (const struct VITAdataBuf *)&iqbuffer2_out, sizeof(iqbuffer2_out), 0, 
	      (struct sockaddr*)&si_LH_portF0, slen);
    if(sentBytes < 0)
      {
      perror("sendto");
      printf("Send to portF, bytes = %i\n",sentBytes);
       }

    }
   }  // end of repeating loop
  }

}


//////////////////////////////////////////////////////////////////////////////
void *sendFlexData(void * threadid){
// forward IQ data from flex to LH in VITA format, with minor mods

// TODO: add 32-bit time stamp & buffer count in right place for use by LH (DRF ddata handler)
  uint64_t theSampleCount = 0;
  fd_set readfd;
  int sockRGout;
  int count;
  if((sockRGout = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)) < 0)
          {
          perror("socket");
          printf("creating sockRGout failed\n");
          }
      else
          {
          printf("sockRGout created\n");
          }
  struct sockaddr_in si_LH_portF0;  // will use sockRGout
  memset((char *) &si_LH_portF0, 0, sizeof(si_LH_portF0));
  si_LH_portF0.sin_family = AF_INET;
  si_LH_portF0.sin_port = htons(LH_DATA_IN_port[0]);
  si_LH_portF0.sin_addr.s_addr = client_addr.sin_addr.s_addr; 

  printf("in Flex DATA thread; start to send data to Port F %i; init sock5\n",LH_DATA_IN_port[0]);
  sock5 = socket(AF_INET, SOCK_DGRAM, 0);
  printf("after socket assign, sock5= %i\n",sock5);
  if(sock5 < 0) {
    printf("sock5 error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
    }
  int yes = 1;  // make socket re-usable
  if(setsockopt(sock5, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes)) == -1) {
   printf("sock5: Error setting sock option SO_REUSEADDR\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
   }

  printf("sock5 created\n");
  int addr_len = sizeof(struct sockaddr_in);
  memset((void*)&flex_addr, 0, addr_len);
  flex_addr.sin_family = AF_INET;
  flex_addr.sin_addr.s_addr = htons(INADDR_ANY);
  flex_addr.sin_port = htons(FLEXDATA_IN);
  printf("bind sock5\n:");
  int ret = bind(sock5, (struct sockaddr*)&flex_addr, addr_len);
  if (ret < 0){
    printf("sock5 (Flex) bind error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
     }
  FD_ZERO(&readfd);
  FD_SET(sock5, &readfd);
  printf("in flex Data thread read from port %i\n",FLEXDATA_IN);
 // client_addr.sin_port = htons(LH_DATA_IN_port[0]);
 ret = 1;
 while(1==1) {  // repeating loop

   if(stopDataColl)
	 {
     puts("UDP thread end");
     ft8active = 0;
     close(sock5);
	 pthread_exit(NULL);
	 }

  if(ret > 0){
   if (FD_ISSET(sock5, &readfd)){
 //   printf("try read\n");
    count = recvfrom(sock5, &iqbuffer2_in, sizeof(iqbuffer2_in),0, (struct sockaddr*)&flex_addr, &addr_len);
  //  printf("bytes received = %i\n",count);
 //   printf("VITA header= %x %x\n",iqbuffer2_in.VITA_hdr1[0],iqbuffer2_in.VITA_hdr1[1]);
 //   printf("stream ID= %x%x%x%x\n", iqbuffer2_in.stream_ID[0],iqbuffer2_in.stream_ID[1], iqbuffer2_in.stream_ID[2],iqbuffer2_in.stream_ID[3]);
    memcpy(iqbuffer2_out.VITA_hdr1, iqbuffer2_in.VITA_hdr1, sizeof(iqbuffer2_out.VITA_hdr1));

    iqbuffer2_out.VITA_packetsize = sizeof(iqbuffer2_out);
    iqbuffer2_out.stream_ID[0] = 0x52;   // put "RG" into stream ID
    iqbuffer2_out.stream_ID[1] = 0x47;
    iqbuffer2_out.stream_ID[2] = 1;   // number of embedded subchannels in buffer
    iqbuffer2_out.stream_ID[3] = iqbuffer2_in.stream_ID[3];
    iqbuffer2_out.time_stamp = (uint32_t)time(NULL);
    iqbuffer2_out.sample_count = theSampleCount;
    theSampleCount++; // this is actually a packet count, at least for now
  //  printf("timestamp = %i \n",iqbuffer2_out.time_stamp);
    for(int i=0; i < 512; i++)
     {
      iqbuffer2_out.theDataSample[i] = iqbuffer2_in.theDataSample[i];
     }

    count = recvfrom(sock5, &iqbuffer2_in, sizeof(iqbuffer2_in),0, (struct sockaddr*)&flex_addr, &addr_len);
 //   printf("bytes received = %i\n",count);

    for(int i=0; i < 512; i++)
     {
      iqbuffer2_out.theDataSample[i + 512] = iqbuffer2_in.theDataSample[i];
     }
    int slen = sizeof(si_LH_portF0);
  //  int sentBytes = sendto(sock, (const struct dataBuf *)&iqbuffer2_out, sizeof(iqbuffer2_out), 0, 
	//      (struct sockaddr*)&portF_addr, sizeof(portF_addr));

  //  printf(" dest IP addr = %s\n",inet_ntoa(si_LH_portF0.sin_addr));
  //  printf(" dest port = %d\n",(int)ntohs(si_LH_portF0.sin_port));
    int sentBytes = sendto(sockRGout, (const struct VITAdataBuf *)&iqbuffer2_out, sizeof(iqbuffer2_out), 0, 
	      (struct sockaddr*)&si_LH_portF0, slen);
    if(sentBytes < 0)
      {
      perror("sendto");
      printf("Send to portF, bytes = %i\n",sentBytes);
       }

    }
   }  // end of repeating loop
  }

}

//////////// Listen for and process CC commands ///////////////////////////////////////
void *awaitCreateChannels(void *threadid) {

  char buffer[1024];
  int addr_len;
  int ret;
  int count;
  int optval;
  printf("Starting awaitCreateChannels thread, listening on Port %d (Port B)\n",CCport); 

  addr_len = sizeof(struct sockaddr_in);
  memset((void*)&server_addr, 0, addr_len);
  server_addr.sin_family = AF_INET;
  server_addr.sin_addr.s_addr = htons(INADDR_ANY);

// set up for Port B reply
  server_addr.sin_port = htons(CCport);
 // server_addr.sin_port = CCport;
  printf("DEmain, bind sock1 to %s port  %i (%i)\n",inet_ntoa(server_addr.sin_addr),ntohs(server_addr.sin_port),CCport);
  ret = bind(sock1, (struct sockaddr*)&server_addr, addr_len);
  if (ret < 0) {
    perror("bind error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
    }

while(1)
   {
    printf("DE: Awaiting CC to come in on port B  %u\n", CCport);
    count = recvfrom(sock1, buffer, CCport , 0, (struct sockaddr*)&server_addr, &addr_len);
   // LH_port = ntohs(client_addr.sin_port);
    printf("command recd %c%c %x %x %x %x from port %d, bytes=%d\n",buffer[0],buffer[1],buffer[2],buffer[3],buffer[4],buffer[5], ntohs(LH_port),count);


     if(memcmp(buffer, DATARATE_INQUIRY, 2) == 0)
      {
      printf(" ******** DATARATE INQUIRY received \n");
      sleep(0.2);
      DATARATEBUF myDataRateBuf;
      memset(&myDataRateBuf,0,sizeof(myDataRateBuf));
      strncpy(myDataRateBuf.buftype, "DR",2);
      myDataRateBuf.dataRate[0].rateNumber= 1;
      myDataRateBuf.dataRate[0].rateValue = 8;
      myDataRateBuf.dataRate[1].rateNumber= 2;
      myDataRateBuf.dataRate[1].rateValue = 4000;
      myDataRateBuf.dataRate[2].rateNumber= 3;
      myDataRateBuf.dataRate[2].rateValue = 8000;
      myDataRateBuf.dataRate[3].rateNumber= 4;
      myDataRateBuf.dataRate[3].rateValue = 48000;
      myDataRateBuf.dataRate[4].rateNumber= 5;
      myDataRateBuf.dataRate[4].rateValue = 96000;
      myDataRateBuf.dataRate[5].rateNumber= 6;
      myDataRateBuf.dataRate[5].rateValue = 192000;
      myDataRateBuf.dataRate[6].rateNumber= 7;
      myDataRateBuf.dataRate[6].rateValue = 384000;
      myDataRateBuf.dataRate[7].rateNumber= 8;
      myDataRateBuf.dataRate[7].rateValue = 768000;
      myDataRateBuf.dataRate[8].rateNumber= 9;
      myDataRateBuf.dataRate[8].rateValue = 1536000;


   //   client_addr.sin_port = htons(LH_CONF_IN_port[channelNo] ); 

      client_addr.sin_port = LH_port;  // reply to port A

      printf("Sending Datarate response to LH\n");
      count = 0;
      count = sendto(sock1, &myDataRateBuf, sizeof(myDataRateBuf), 0, (struct sockaddr*)&client_addr, addr_len);
      printf("Response: DATARATEBUF of %u bytes sent to LH port %u \n ",count, LH_port) ;

      }


    if(strncmp(buffer, CREATE_CHANNEL ,2) == 0)
      {
      int channelNo =0;
  // update to handle free form string input
      const char s[2] = " ";
      char *operand;
      operand = strtok(buffer, s);
      
      printf("operand = %s\n",operand);
      operand = strtok(NULL, s);
      printf("channel# = %s\n",operand);
      channelNo = atoi(operand);

      operand = strtok(NULL, s);
      printf("port C = %s\n",operand);
      LH_CONF_IN_port[channelNo] = atoi(operand);

      operand = strtok(NULL, s);
      printf("port F = %s\n",operand);
      LH_DATA_IN_port[channelNo] = atoi(operand);
     
      char configReply[20] = "";

      printf("ports set up; now set up sock\n");
      if (sock = socket(AF_INET, SOCK_DGRAM, 0) == -1)
          printf("creating sock failed\n");  // set up for sending to port F
      else
          printf("sock created\n");

      addr_len = sizeof(struct sockaddr_in);
      memset((void*)&portF_addr, 0, addr_len);
      portF_addr.sin_family = AF_INET;
   //   portF_addr.sin_addr.s_addr = htons(LH_IP);
      portF_addr.sin_addr.s_addr = client_addr.sin_addr.s_addr;
      portF_addr.sin_port = htons(LH_DATA_IN_port[channelNo]);
      printf("Bind to port %i\n",LH_DATA_IN_port[channelNo]);

      ret = bind(sock, (struct sockaddr*)&portF_addr, addr_len);
      printf("bind ret=%i\n",ret);
      // set this befoe we change the buffer to reflect DE port setup
  //    client_addr.sin_port = htons(LH_CONF_IN_port[channelNo]);   // the ACK ges back to Port C
      client_addr.sin_port = LH_port;   // the ACK ges back to Port A
      printf("Set up the AK\n");
    //  strncpy(d.myConfigBuf.cmd, "AK", 2);
     
   //   d.myConfigBuf.configPort = DE_CH_IN_port[channelNo]; // this is port D for this channel
   //   d.myConfigBuf.dataPort = 0;  // this is Port E (mic) - currently unused
      printf("Sending AK to port %i\n",ntohs(client_addr.sin_port) );
      sprintf(configReply,"AK %i %i %i",channelNo,DE_CH_IN_port[channelNo],0);
   //   count = sendto(sock1, d.mybuf1, sizeof(d.myConfigBuf), 0, (struct sockaddr*)&client_addr, addr_len);
      count = sendto(sock1, configReply, sizeof(configReply), 0, (struct sockaddr*)&client_addr, addr_len);
      printf("response %s, bytes = %d  sent to ", configReply, count);
      printf(" IP: %s, Port: %d\n", 
      inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

  //   cmdport = DE_CONF_IN_portB;  // all further commands come in here
    }
    
    if(strncmp(buffer, MEM_WRITE ,2) == 0)
      {
      printf("Memory write command received.\n");
      
       const char s[2] = " ";
      char *operand;
      operand = strtok(buffer, s);
      
      printf("operand = %s\n",operand);
      operand = strtok(NULL, s);
      printf("slot# = %s\n",operand);
    //  channelNo = atoi(operand);

      operand = strtok(NULL, s);
      printf("interface = %s\n",operand);
    //  LH_CONF_IN_port[channelNo] = atoi(operand);

      operand = strtok(NULL, s);
      printf("address = %s\n",operand);
    //  LH_DATA_IN_port[channelNo] = atoi(operand);
    
      operand = strtok(NULL, s);
      printf("data = %s\n",operand);
      char configReply[20] = "";
      printf("Sending AK to port %i\n",ntohs(client_addr.sin_port) );
      sprintf(configReply,"AK \n");
   //   count = sendto(sock1, d.mybuf1, sizeof(d.myConfigBuf), 0, (struct sockaddr*)&client_addr, addr_len);
      count = sendto(sock1, configReply, sizeof(configReply), 0, (struct sockaddr*)&client_addr, addr_len);
      
      
      
      
      }
    
   }
  return 0;

}


void *handleCommands(void* c) 
 {
  int channelNo = (int)c;
  printf("Starting command processor for channel %i\n",channelNo);

  while (LH_CONF_IN_port[channelNo] == 0)
  {
   //printf("LH_CONF_IN_port[ %i ] = %i\n",channelNo, LH_CONF_IN_port[channelNo]);
   sleep(0.1);

  } ;

  printf("Starting channel %i command processing\n",channelNo);
  printf("Port = %i\n",LH_CONF_IN_port[channelNo] );

  char workBuf[1024];

  int addr_len;
  int ret;
  int count;
  int optval;
  int sock2;
// create & bind socket for inbound config packets
  fd_set readcfg;
  sock2 = socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
  setsockopt(sock2, SOL_SOCKET, SO_REUSEADDR, (const void *)&optval, sizeof(int));
  if(sock2 < 0 ) { perror("sock2 error\n"); return (void *) -1; }
  addr_len = sizeof(struct sockaddr_in);
  memset((void*)&config_in_addr,0,addr_len);
  config_in_addr.sin_family = AF_INET;
  config_in_addr.sin_addr.s_addr = htons(INADDR_ANY);
  config_in_addr.sin_port = htons(DE_CH_IN_port[channelNo]);  // listen on Port D
  ret = bind(sock2,(struct sockaddr *)&config_in_addr,addr_len);
  if(ret < 0) { perror("sock2 bind error\n"); return (void *) -1; }
  
  while(1)
    {
    memset(&workBuf,0,sizeof(workBuf));  // clear this area
    printf("Ready to receive command on port D = %i\n", DE_CH_IN_port[channelNo]);
 //   count = recvfrom(sock2, cb.configBuffer, sizeof(cb.configBuffer) , 0, 
 //       (struct sockaddr*)&config_in_addr, &addr_len);
    count = recvfrom(sock2, workBuf, sizeof(workBuf) , 0, 
        (struct sockaddr*)&config_in_addr, &addr_len);

    printf("Command %s received into channel %i\n",workBuf,channelNo);

    if(memcmp(workBuf, STATUS_INQUIRY, 2) == 0)
      {
      printf("STATUS INQUIRY received\n");
      client_addr.sin_port = htons(LH_CONF_IN_port[channelNo] ); 
      count = 0;
      count = sendto(sock1, "OK", 2, 0, (struct sockaddr*)&client_addr, addr_len);
      printf("Response OK = %u bytes sent to LH port %u \n ",count, LH_CONF_IN_port[channelNo]) ;
      }

    // is this CH command?
    if(memcmp(workBuf, CONFIG_CHANNELS, 2) == 0)
      {

    //  memcpy(workBuf,&cmdBuf,count);
      printf(" **********  CONFIG CHANNELS received %s\n", workBuf);
      int channelNo =0;  // TODO: this is unnecessary, may conflict with actual value
  // update to handle free form string input
      const char s[2] = " ";
      char *operand;
      operand = strtok(workBuf, s);  // this is the "CH"
      
      printf("operand = %s\n",operand);
      operand = strtok(NULL, s);
      printf("channel# = %s\n",operand);
      channelNo = atoi(operand);

      operand = strtok(NULL, s);  // VUTA standard indicator
      printf("VITA type = %s\n",operand);    

      operand = strtok(NULL, s);  // # of subchannels
      printf("subchannels= %s\n",operand);  

      noOfChannels = atoi(operand);

      operand = strtok(NULL, s);  // speed
      printf("samples/sec= %s\n",operand);
      dataRate = atoi(operand);
    
      for (int i=0; i < noOfChannels; i++) 
        {


        operand = strtok(NULL, s); // subchannel no
        int sNo = atoi(operand);
        operand = strtok(NULL, s); // antenna#
        int antNo = atoi(operand);
        operand = strtok(NULL, s); 
        float scfreq = atof(operand);

        printf("Subchannel %i, Port %i, Freq %lf\n", sNo, antNo, scfreq);

        }  

  
      client_addr.sin_port = htons(LH_CONF_IN_port[channelNo] ); 
      count = 0;
      count = sendto(sock1, "AK", 2, 0, (struct sockaddr*)&client_addr, addr_len);
      printf("Response AK = %u bytes sent to LH port %u \n ",count, LH_CONF_IN_port[channelNo]) ;
      } // end of handling CH

    if(memcmp(workBuf, DATARATE_INQUIRY, 2) == 0)
      {
      printf(" ******** DATARATE INQUIRY received \n");
      sleep(0.2);
      DATARATEBUF myDataRateBuf;
      memset(&myDataRateBuf,0,sizeof(myDataRateBuf));
      strncpy(myDataRateBuf.buftype, "DR",2);
      myDataRateBuf.dataRate[0].rateNumber= 1;
      myDataRateBuf.dataRate[0].rateValue = 8;
      myDataRateBuf.dataRate[1].rateNumber= 2;
      myDataRateBuf.dataRate[1].rateValue = 4000;
      myDataRateBuf.dataRate[2].rateNumber= 3;
      myDataRateBuf.dataRate[2].rateValue = 8000;
      myDataRateBuf.dataRate[3].rateNumber= 4;
      myDataRateBuf.dataRate[3].rateValue = 48000;
      myDataRateBuf.dataRate[4].rateNumber= 5;
      myDataRateBuf.dataRate[4].rateValue = 96000;
      myDataRateBuf.dataRate[5].rateNumber= 6;
      myDataRateBuf.dataRate[5].rateValue = 192000;
      myDataRateBuf.dataRate[6].rateNumber= 7;
      myDataRateBuf.dataRate[6].rateValue = 384000;
      myDataRateBuf.dataRate[7].rateNumber= 8;
      myDataRateBuf.dataRate[7].rateValue = 768000;
      myDataRateBuf.dataRate[8].rateNumber= 9;
      myDataRateBuf.dataRate[8].rateValue = 1536000;


      client_addr.sin_port = htons(LH_CONF_IN_port[channelNo] ); 

     // client_addr.sin_port = LH_port;  // reply to port A

      printf("Sending Datarate response to LH\n");
      count = 0;
      count = sendto(sock1, &myDataRateBuf, sizeof(myDataRateBuf), 0, (struct sockaddr*)&client_addr, addr_len);
      printf("Response: DATARATEBUF of %u bytes sent to LH port %u \n ",count, LH_port) ;

      }

    if(memcmp(workBuf, FIREHOSE_SERVER, 2)==0)
      {
      printf("SWITCHING TO FIREHOSE-L MODE; channel#%i\n",channelNo);

      const char s[2] = " ";
      char *operand;
      operand = strtok(workBuf, s);  // this is the "FH"
      
      printf("operand = %s\n",operand);
      operand = strtok(NULL, s);
      strcpy(FH_DATA_IN_IP, operand); 
      printf("IP = '%s'\n",FH_DATA_IN_IP);
      
      operand = strtok(NULL, s);

      FH_DATA_IN_port = atoi(operand);
      printf("port = %i\n",FH_DATA_IN_port);
      firehoseLmode = 1; // set mode; applies only for Channel 0

      }
    if(memcmp(workBuf, STOP_FIREHOSE, 2)==0)
      {
      printf("Switch mode out of Firehose-L\n");
      firehoseLmode = 0;
      }


// Is this a command to start data collection?  
// For simplicity, we assign RG to channel 0, FT8 to channel 1, WSPR to channel 2

    if (memcmp(workBuf, START_DATA_COLL ,2)==0 && channelNo == 0)
	  {
	  printf("START DATA COLLECTION on channel %i;starting sendData\n",channelNo);


      int channelNo =0;
  // update to handle free form string input
      const char s[2] = " ";
      char *operand;
      operand = strtok(workBuf, s);  // this is the "SC"
      
      printf("operand = %s\n",operand);
      operand = strtok(NULL, s);
      printf("channel# = %s\n",operand);
      channelNo = atoi(operand);


	  stopDataColl = 0;
  	  long j = 1;
  	  pthread_t datathread;
      int rc = 0;
      if(firehoseLmode)
        {
  	    rc = pthread_create(&datathread, NULL, sendFHData, (void *)j);
        }
      else
        {
  	    rc = pthread_create(&datathread, NULL, sendFlexData, (void *)j);
        }
  	  printf("thread start rc = %d\n",rc);

      client_addr.sin_port = htons(LH_CONF_IN_port[channelNo] ); 
   //   client_addr.sin_port = htons(40001);  // TODO -must compute correctly
      count = 0; 
      sleep(0.25); 
      count = sendto(sock1, "AK", 2, 0, (struct sockaddr*)&client_addr, addr_len);
      printf("DE Response AK = %u bytes sent to LH addr %s port %u \n ",count, 
                inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port)) ;
      continue;
      }

    if(memcmp(workBuf, STOP_DATA_COLL,2)==0 && channelNo == 0)
      {
      printf("* * * * STOP DATA COLL received * * * *\n");

      int channelNoVerify =0;
  // update to handle free form string input
      const char s[2] = " ";
      char *operand;
      operand = strtok(workBuf, s);  // this is the "SC"
      
      printf("operand = %s\n",operand);
      operand = strtok(NULL, s);
      printf("channel# = %s\n",operand);
      channelNoVerify = atoi(operand);

      if(channelNoVerify == channelNo)
        printf("Received channelNo matches expected value of 0\n");
     else
        printf("* * * ERROR * * * Received channelNoVerify = %i; expected 0",channelNoVerify);

      stopDataColl = 1;

      client_addr.sin_port = htons(LH_CONF_IN_port[channelNo] ); 
      count = 0;
      count = sendto(sock1, "AK", 2, 0, (struct sockaddr*)&client_addr, addr_len);
      printf("Response AK = %u bytes sent to LH port %u \n ",count, LH_CONF_IN_port[channelNo]) ;
      continue;
      }


    if ( (memcmp(workBuf, START_DATA_COLL,2)==0) && channelNo == 1)  // 
     {
      printf("Start FlexRadio / FT8 command received; starting thread\n");
      stopft8 = 0;
      pthread_t thread1;
      int rc = pthread_create(&thread1, NULL, sendFT8flex, NULL);
      printf("thread start rc = %d\n",rc);
      client_addr.sin_port = htons(LH_CONF_IN_port[channelNo] ); 
      count = 0;
      count = sendto(sock1, "AK", 2, 0, (struct sockaddr*)&client_addr, addr_len);
      printf("Response AK = %u bytes sent to LH port %u \n ",count, LH_CONF_IN_port[channelNo]) ;
      continue;
     }

    if(memcmp(workBuf, STOP_DATA_COLL,2)==0  && channelNo == 1)
      {
      printf("* * * * STOP DATA COLL (FT8) received * * * *\n");
      stopft8 = 1;

      client_addr.sin_port = htons(LH_CONF_IN_port[channelNo] ); 
      count = 0;
      count = sendto(sock1, "AK", 2, 0, (struct sockaddr*)&client_addr, addr_len);
      printf("Response AK = %u bytes sent to LH port %u \n ",count, LH_CONF_IN_port[channelNo]) ;
      continue;
      }

    if ( (memcmp(workBuf, START_DATA_COLL, 2)==0) && channelNo == 2)  // 
     {
      printf("Start FlexRadio / WSPR command received; starting thread\n");
      stopwspr = 0;
      pthread_t thread1;
      int rc = pthread_create(&thread1, NULL, sendwsprflex, NULL);
      printf("thread start rc = %d\n",rc);
      client_addr.sin_port = htons(LH_CONF_IN_port[channelNo] ); 
      count = 0;
      count = sendto(sock1, "AK", 2, 0, (struct sockaddr*)&client_addr, addr_len);
      printf("Response AK = %u bytes sent to LH port %u \n ",count, LH_CONF_IN_port[channelNo]) ;
      continue;
     }

    if(memcmp(workBuf, STOP_DATA_COLL,2)==0  && channelNo == 2)
      {
      printf("* * * * STOP DATA COLL (WSPR)received * * * *\n");
      stopwspr = 1;

      client_addr.sin_port = htons(LH_CONF_IN_port[channelNo] ); 
      count = 0;
      count = sendto(sock1, "AK", 2, 0, (struct sockaddr*)&client_addr, addr_len);
      printf("Response AK = %u bytes sent to LH port %u \n ",count, LH_CONF_IN_port[channelNo]) ;
      continue;
      }



    }
///////////////////// end of command processing section ////////////////

  

}



/////////////////////////////////////////////////////////////////////
void discoveryReply(char buffer[1024]) {
  fprintf(stderr,"discovery packet detected\n"); 
  buffer[10] = 0x07;
  LH_port = ntohs(client_addr.sin_port);
	 
  printf("\nDiscovery 2, Client connection information:\n\t IP: %s, Port: %d\n", 
             inet_ntoa(client_addr.sin_addr), LH_port);
  int count = sendto(sock, buffer, 60, 0, (struct sockaddr*)&client_addr,
		 sizeof(client_addr));
}

///////////////////////////////////////////////////////////////////////////////////
int *run_DE(void) 
  {
  stoplink = 0;
  stopData = 0;
  stopft8 = 0;
  ft8active = 0;
  config_busy = 0;
  int addr_len;
  int count;
  int ret;
  //DE_CONF_IN_portD = 50001;  //fixed port on which to receive config request (CC)


  fd_set readfd;
  char buffer[1024];

  sock = socket(AF_INET, SOCK_DGRAM, 0);  // for sending flex spectrum data out
  if (sock < 0) {
    perror("sock error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
    }

  sock1 = socket(AF_INET, SOCK_DGRAM, 0);  // for reply via Port B
  if (sock1 < 0) {
    perror("sock1 error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
    }



  sock5 = socket(AF_INET, SOCK_DGRAM, 0);  // for receiving IQ packets from FlexRadio (RG)
  if (sock5 < 0) {
    perror("sock5 error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
    }

  sockft8out = socket(AF_INET, SOCK_DGRAM, 0);  // for sending ft8 data out
  if (sockft8out < 0) {
    perror("sockft8out error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
    }

  sockwsprout = socket(AF_INET, SOCK_DGRAM, 0);  // for sending wspr data out
  if (sockwsprout < 0) {
    perror("sockwsprout error\n");
    int r=-1;
    int *ptoi;
    ptoi = &r;
    return (ptoi);
    }


  pthread_t thread3;
  printf("Starting awaitConfigChannels\n");
  int rc = pthread_create(&thread3, NULL, awaitCreateChannels, NULL);
  printf("retcode after thread create = %i\n",rc);

  printf("awaitCC started; startng command processing thread\n");
  pthread_t thread4[3];
  int c0 = 0;
  rc = pthread_create(&thread4[0], 0, handleCommands, (void*)c0);

  int c = 1;
  rc = pthread_create(&thread4[1], 0, handleCommands, (void*)c);


  int c2 = 2;
  rc = pthread_create(&thread4[2], 0, handleCommands, (void*)c2);
  
  rc = pthread_join(thread3, NULL);  // here we wait for channel creation
  
  // thread3 will never complete (intentianally)
  
  
}

int main(int argc, char** argv) {
 //while(1)
 {
// arguments are:
//  1 - port B
//  2 - IP addr of LH
//  3 - port A
 printf("- - - - - Starting DEmain; port B = %s\n",argv[1]);

// port on which to await CC   (create channel request)
 CCport = atoi(argv[1]);  // port B
 LH_port = ntohs(atoi(argv[3]));
 inet_pton(AF_INET, argv[2], &client_addr.sin_addr);  // LH IP addr
 inet_pton(AF_INET, argv[2], &LH_IP);  // this is not used TODO; fix
 client_addr.sin_port = LH_port;  // port A
 
 int *r =  run_DE();
 printf("DE exited, rc = %i; closing sockets & threads\n", *r);
 close(sock);
 close(sock1);
 //close(sock2);
 stoplink = 1;
 stopData = 1;
 stopft8 = 1;
 printf("attempting restart\n");
 }

}



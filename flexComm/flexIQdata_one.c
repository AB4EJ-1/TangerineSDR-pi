/* Copyright (C) 2019 The University of Alabama
* Author: William (Bill) Engelke, AB4EJ
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
* Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
*
* External packages:

*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/types.h>
#include <net/if_arp.h>
#include <net/if.h>
#include <errno.h>
#include <netdb.h>
#include <netinet/in.h>
#include <pthread.h>

#define FLEXRADIO_IP "192.168.1.66"
#define FLEX_DISCOVERY_PORT 4992
#define UDPPORT_IN 7791
#define UDPPORT_OUT 7100

struct flexDataSample
  {
  float I_val_int;
  float Q_val_int;
  };

typedef struct flexDataBuf
 {
 char VITA_hdr1[2];  // rightmost 4 bits is a packet counter
 int16_t  VITA_packetsize;
 char stream_ID[4];
 char class_ID[8];
 uint32_t time_stamp;
 uint64_t fractional_seconds;
 struct flexDataSample flexDatSample[512];
 } FLEXBUF;

static struct sockaddr_in flex_tcp_addr;
static struct sockaddr_in flex_udp_addr;
static int sock, tcpsock;  // sockets
static char flex_reply[3000];
static  int fd;
static struct flexDataBuf iqbuffer;

void *receiveFlexAnswers(void *threadid) {
 printf("reply receive thread start\n");

while(1==1) {
 memset(flex_reply, 0, sizeof(flex_reply));
 int c = recv(sock,flex_reply, sizeof(flex_reply) ,0);
 printf("\n---------------------\n");
  //printf("Flex replied with %i bytes: %s\n",c,flex_reply);
 for(int i = 9; i < 450; i++)
   {
  // if(flex_reply[i] == 0x00) break;
   printf("%c",flex_reply[i]);
   }
 printf("\n---------------------\n");
 }
}

void main () {

 int r, c;
// char command1[25] = "c0|client udpport 7790\n";
 char command1[50] = "c0|client udpport 7790\n";
 char command2[100] = "c1|stream create daxiq=1 port=7790\n";
 char commandstop1[100] = "c7|stream remove 0x20000000\n";

 memset(flex_reply, sizeof(flex_reply),0);
 int flexport = UDPPORT_IN;
 sock = socket(AF_INET, SOCK_STREAM, 0);  // set up socket for TCP comm to Flex
 if (sock == -1)
   {
   printf("Error, could not create TCP socket\n");
   }
  else
   printf("TCP socket created\n");

 flex_tcp_addr.sin_addr.s_addr = inet_addr(FLEXRADIO_IP);
 flex_tcp_addr.sin_family      = AF_INET;
 flex_tcp_addr.sin_port        = htons(FLEX_DISCOVERY_PORT);

 pthread_t threadId;
 int rc = pthread_create(&threadId, NULL, &receiveFlexAnswers, NULL);

 if(connect(sock, (struct sockaddr *)&flex_tcp_addr, sizeof(flex_tcp_addr)) < 0)
  {
  printf("Error - could not connect to flex\n");
  }
 else
  {
   printf("Connected...\n");

  while(1)
   {
   printf("1 - start Flex data\n2 - stop Flex data\n");
   r = getchar();
   printf("user entered %i\n",r);
   if(r == 49)  // decimal version of 1
    {
    c = send(sock,command1, strlen(command1),0);
    printf("sent %s\n",command1);
    sleep(3);   
    c = send(sock,command2, strlen(command2),0);
    printf("sent %s\n",command2);
    sleep(3);
    }
 
   if(r == 50)  // decimal version of 2
    {
    c = send(sock,commandstop1, strlen(commandstop1),0);
    printf("sent %s\n",commandstop1);
    sleep(3);
    }
   }
  return;

 }
}

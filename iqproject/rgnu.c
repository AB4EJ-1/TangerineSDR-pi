/*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.*

*/ 
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <pthread.h>
#include <string.h>
#include "de_signals.h"
#include <unistd.h>
#include <sys/time.h>

// following should be the IP address of computer running Gnuradio
#define DESTINATION "192.168.1.207"
#define INPUT_PORT "7790"
#define SA struct sockaddr

struct sockaddr_in recv_data_addr;    // for data coming from DE

static uint16_t LH_DATA_IN_port;

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

uint64_t GetTimeStamp() {
  struct timeval tv;
  gettimeofday(&tv,NULL);
  return tv.tv_sec*(uint64_t)1000000+tv.tv_usec;

}

int main() {

  LH_DATA_IN_port = atoi(INPUT_PORT);
  int sock;
  struct sockaddr_in si_LH;
  //struct flexDataBuf myDataBuf;
  struct flexDataBuf myDataBuf;
  printf("rgnu: starting rgnu\n");
  printf("create receciving socket\n");
    if ( (sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)) < 0)
    {
    perror("socket error");
    exit(-1);
    }

  memset((char *) &si_LH, 0, sizeof(si_LH));
  si_LH.sin_family = AF_INET;
  si_LH.sin_port = htons(LH_DATA_IN_port);
  si_LH.sin_addr.s_addr = htonl(INADDR_ANY);
  printf("bind receiving socket\n");
  if (bind(sock, (struct sockaddr *)&si_LH, sizeof(si_LH)) < 0)
    {
    perror("bind error");
    exit(-1);
    }

  // setup for sending UDP stream data to GNUradio
  int sockfd, connfd;
  struct sockaddr_in servaddr, cli;
  bzero(&servaddr, sizeof(servaddr));
  servaddr.sin_family = AF_INET;
  servaddr.sin_port = htons(8790);
  
  if(inet_aton(DESTINATION,&servaddr.sin_addr) == 0)
    {
    printf("inet_aton failed\n");
    exit(1);
    }
  
  printf("create outbound socket\n");
  sockfd = socket(AF_INET, SOCK_DGRAM,IPPROTO_UDP);

  printf("connect outbound socket\n");
  if(connect(sockfd, (SA*)&servaddr, sizeof(servaddr)) != 0)
    {
    printf("\nRG: Could not connect to GNUradio port\n\n");
    }
  else
    printf("\nRG: GNUradio connected!  bufsize = %li\n\n",sizeof(myDataBuf.flexDatSample));
  printf("start listening to 7790\n");
while(1)
 {
 // start listening loop here
  int slen = sizeof(si_LH);
  int recv_len;
  if( (recv_len = recvfrom(sock, &myDataBuf, sizeof(myDataBuf), 0, 
      (struct sockaddr *) &si_LH, &slen)) < 0)
    {
    perror("recvfrom error");
    exit(-1);
    }
    
  printf("time %li,received %i bytes, try to resend - ",GetTimeStamp(),recv_len);
  int n = sendto(sockfd, (const char*)myDataBuf.flexDatSample, sizeof(myDataBuf.flexDatSample), MSG_CONFIRM,
            (const struct sockaddr *) &servaddr, sizeof(servaddr));
  printf(" bytes sent = %i \n",n);
    
    
 }    
  
  
  }

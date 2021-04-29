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
//#include <libconfig.h>
#include "de_signals.h"
#include <unistd.h>


#define SA struct sockaddr

struct sockaddr_in recv_data_addr;    // for data coming from DE

static uint16_t LH_DATA_IN_port;



int main() {

  LH_DATA_IN_port = atoi("8890");
  int sock;
  struct sockaddr_in si_LH;
  struct VITAdataBuf myDataBuf;
  printf("RGrcv: starting rgnu\n");
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

  //buffers_received = 0; // initialize this

    
  // setup for sending UDP stream data to GNUradio
  int sockfd, connfd;
  struct sockaddr_in servaddr, cli;
  
  servaddr.sin_addr.s_addr = inet_addr("192.168.1.207");
  int servport = atoi("8790");
  servaddr.sin_port = htons(servport);
  printf("create outbound socket\n");
 // bzero(tcpBUFF, sizeof(tcpBUFF));
  sockfd = socket(AF_INET, SOCK_DGRAM,0);
  bzero(&servaddr, sizeof(servaddr));
  servaddr.sin_family = AF_INET;
  printf("connect outbound socket\n");
  if(connect(sockfd, (SA*)&servaddr, sizeof(servaddr)) != 0)
    {
    printf("\nRG: Could not connect to GNUradio port\n\n");
    }
  else
    printf("\nRG: GNUradio connected!  bufsize = %i\n\n",sizeof(myDataBuf.theDataSample));
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
    
  printf("received %i bytes, try to resend\n",recv_len);
  int n = sendto(sockfd, (const char*)myDataBuf.theDataSample, sizeof(myDataBuf.theDataSample), MSG_CONFIRM,
            (const struct sockaddr *) &servaddr, sizeof(servaddr));
    
    
 }    
  
  
  }

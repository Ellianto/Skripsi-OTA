// Credits to https://www.tenouk.com/Module41c.html
// With minor changes and adjustments from:
// https://gist.github.com/hostilefork/f7cae3dc33e7416f2dd25a402857b6c6

// For Linux Only, Probably ARM Based Embedded Devices are linux based
// If Windows, build and run on WSL 
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

struct sockaddr_in local_sock;
struct ip_mreq group;

int sd;
int datalen;
char databuf[1024];


int main() {
    // Create the Datagram Socket
    sd = socket(AF_INET, SOCK_DGRAM, 0);

    if(sd < 0){
        perror("Opening Datagram Socket Error!");
        exit(1);
    } else {
        printf("Opening Datagram Socket...\n");
    }

    // Enable SO_REUSEADDR so multiple instance of this app
    // Can receive copies to the multicast datagrams
    int reuse = 1;
    if(setsockopt(sd, SOL_SOCKET, SO_REUSEADDR, (char *)&reuse, sizeof(reuse)) < 0){
        perror("Seting SO_REUSEADDR Error!");
        close(sd);
        exit(1);
    } else {
        printf("Setting SO_REUSEADDR...\n");
    }

    // Bind the proper port number to the localSock
    memset((char *) &local_sock, 0, sizeof(local_sock));
    local_sock.sin_family = AF_INET;
    local_sock.sin_port   = htons(5432); // Match it with the sender's port
    local_sock.sin_addr.s_addr = htonl(INADDR_ANY); // listens to any multicast group

    if(bind(sd, (struct sockaddr*)&local_sock, sizeof(local_sock))){
        perror("Binding datagram socket error!");
        close(sd);
        exit(1);
    } else {
        printf("Binding datagram socket...\n");
    }

    // Join the multicast group in address 224.255.255.255 on any interface
    group.imr_multiaddr.s_addr = inet_addr("224.255.255.255");
    group.imr_interface.s_addr = htonl(INADDR_ANY);

    if(setsockopt(sd, IPPROTO_IP, IP_ADD_MEMBERSHIP, (char *)&group, sizeof(group)) < 0){
        perror("Adding Multicast Group Error!");
        close(sd);
        exit(1);
    } else {
        printf("Adding multicast group success...\n");
    }

    // Read data coming into socket
    datalen = sizeof(databuf);
    if(read(sd, databuf, datalen) < 0){
        perror("Reading datagram message error!");
        close(sd);
        exit(1);
    } else {
        printf("Reading datagram message...\n");
        printf("Message from Multicast Server is : %s\n", databuf);
    }

    return 0;
}
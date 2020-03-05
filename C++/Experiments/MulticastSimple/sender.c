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

struct in_addr local_interface;
struct sockaddr_in group_sock;

int sd;

char databuf[1024] = "Just a Multicast Message";
int datalen = sizeof(databuf);

int main() {
    // Create a Datagram socket
    sd = socket(AF_INET, SOCK_DGRAM, 0);

    if (sd < 0){
        perror("Opening Datagram Socket Error!");
        exit(1);
    } else {
        printf("Opening the Datagram Socket...\n");
    }

    // Initializing group sockaddr structure
    // with address 224.255.255.255 port 5432
    memset((char *) &group_sock, 0, sizeof(group_sock));
    group_sock.sin_family = AF_INET;
    group_sock.sin_addr.s_addr = inet_addr("224.255.255.255");
    group_sock.sin_port = htons(5432);

    // Set the Local Interface for outbound multicast datagrams
    // The IP Addr specified must be bound with a local, multicast capable interface
    // local_interface.s_addr = inet_addr("192.168.56.1");

    // if(setsockopt(sd, IPPROTO_IP, IP_MULTICAST_IF, (char *)&local_interface, sizeof(local_interface)) < 0){
    //     perror("Setting local interface error!");
    //     exit(1);
    // } else {
    //     printf("Setting the local interface...\n");
    // }

    // Send message to the specified multicast group
    // specified in the group_sock structure
    if(sendto(sd, databuf, datalen, 0,(struct sockaddr*)&group_sock, sizeof(group_sock)) < 0){
        perror("Sending Datagram Message Error!");
    } else {
        printf("Successfully sent datagram message!\n");
    }

    /**
     * You can disable the loopback interface so that you did not receive your own datagram
     * 
     * char loopch = 0;
     * if(setsockopt(sd, IPPROTO_IP, IP_MULTICAST_LOOP, (char *)&loopch, sizeof(loopch)) < 0){
     *  perror("Setting IP_MULTICAST_LOOP Error!");
     *  close(sd);
     *  exit(1);
     * } else {
     *  print("Disabled Loopback Interface for Multicast\n");
     * }
     * 
     * If it is not disabled, after sending the datagram you can listen for the datagram via loopback interface
     * 
     * if(reqd(sd, databuf, datalen) < 0){
     *  perror("Reading Datagram Message Error!");
     *  close(sd);
     *  exit(1);
     * } else {
     *  print("Reading the datagram message from client...");
     *  print("Message is : %s\n", databuf);
     */
    return 0;
}


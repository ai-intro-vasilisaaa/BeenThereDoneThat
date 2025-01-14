import socket
import threading
import time
import struct
import os

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
PACKET_SIZE = 1024
HEADER_SIZE = 21
PAYLOAD_SIZE = PACKET_SIZE - HEADER_SIZE

# Global shutdown signal
shutdown_event = threading.Event()

"""
The Broadcast offer function
Sends offer messages according to the format using broadcast in port 37020 that's decided ahead 
(maybe not what we're supposed to do im not sure)
Will stop when the shutdown event is triggered
"""
def broadcast_offer(broadcast_sock, server_udp_port, server_tcp_port, broadcast_interval=1):
    """Broadcast offer messages every second."""
    broadcast_addr = ('<broadcast>', 37020)
    while not shutdown_event.is_set():
        offer_message = struct.pack(
            '!LBHH',
            MAGIC_COOKIE,
            OFFER_MESSAGE_TYPE,
            server_udp_port,
            server_tcp_port
        )
        broadcast_sock.sendto(offer_message, broadcast_addr)
        time.sleep(broadcast_interval)
    print(f"{RED}Broadcast thread stopped.{RESET}")

"""
Just listen to incoming connections on the socket and runs
the tcp handle thread for each connection
"""
def tcp_listen(tcp_server_sock):
    try:
        while not shutdown_event.is_set():
            conn, addr = tcp_server_sock.accept()
            threading.Thread(target=handle_tcp_client, args=(conn, addr,)).start()
    except OSError:
        print(f"{RED}TCP thread stopped.{RESET}")

"""
Still need to refine
"""
def handle_tcp_client(conn, addr):
    print(f"{CYAN}TCP connection established with {addr}{RESET}")
    try:
        # Receive request message
        header = conn.recv(5)
        magic_cookie, message_type = struct.unpack('!LB', header)
        if magic_cookie != MAGIC_COOKIE or message_type != REQUEST_MESSAGE_TYPE:
            print(f"{RED}Invalid request from {addr}{RESET}")
            return
        file_size_encoded = b""
        while True:
            byte = conn.recv(1)
            if not byte or byte == b"\n":  # Stop at newline
                break
            file_size_encoded += byte
        # Convert the file size string to an integer
        try:
            file_size = int(file_size_encoded.decode())
            print(f"file size: {file_size}")
        except ValueError:
            print(f"{RED}Invalid file size: {file_size_encoded}{RESET}")
        
        # Send payload
        header = struct.pack('!LB', MAGIC_COOKIE, PAYLOAD_MESSAGE_TYPE)
        payload = os.urandom(file_size)
        conn.sendall(header + payload)
        print(f"{GREEN}Sent {file_size} bytes to {addr}{RESET}")
    finally:
        conn.close()

"""
Like the tcp listen, but udp doesn't have connections
"""
def udp_listen(udp_server_sock):
    try:
        while not shutdown_event.is_set():
            data, addr = udp_server_sock.recvfrom(1024)
            threading.Thread(target=handle_udp_client, args=(udp_server_sock, addr, data,)).start()
    except OSError as e:
        print(f"{RED}UDP thread stopped.{e}.{RESET}")


def handle_udp_client(sock, client_addr, request_msg):
    print(f"{CYAN}UDP connection established with {client_addr}{RESET}")
    
    # Receive request message
    magic_cookie, message_type, file_size = struct.unpack('!LBQ', request_msg[:13])
    if magic_cookie != MAGIC_COOKIE or message_type != REQUEST_MESSAGE_TYPE:
        print(f"{RED}Invalid request from {client_addr}{RESET}")
        return
    print("Request validated. Preparing to send file...")
    
    
    # Calculate the number of packets
    num_packets = file_size // PAYLOAD_SIZE  # Each packet is 1024 bytes
    sent_packets = 0

    print("num_packets: ", num_packets)
    
    for i in range(num_packets):
        try:
            header = struct.pack('!LBQQ', MAGIC_COOKIE, PAYLOAD_MESSAGE_TYPE, num_packets, i)
            
            # Build payload
            start = i * PAYLOAD_SIZE
            end = min(start + PAYLOAD_SIZE, file_size)
            payload = b'A' * (end - start)  # Simulated payload data
            
            packet = header + payload  # Combine header and payload

            # Send packet
            sock.sendto(packet, client_addr)
            sent_packets += 1
            
            time.sleep(0.01)  # Simulate packet interval between sends
        except Exception as e:
            print(f"{RED}Error sending packet {i}: {e}{RESET}")
    sock.close()


"""
The main server function
You can change the UDP and TCP ports that will be used in the offer
Starts three threads, the broadcast thread, the UDP listen thread, and the TCP listen thread
When doing CTRL+C will go into shutdown mode using the shutdown event
"""
def server(udp_port=12345, tcp_port=12346):
    host_ip = socket.gethostbyname(socket.gethostname())
    print(f"{CYAN}Server started, listening on IP address {host_ip}{RESET}")
    
    # Start the offer broadcast thread
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_thread = threading.Thread(target=broadcast_offer, args=(broadcast_sock, udp_port, tcp_port), daemon=True)
    broadcast_thread.start()
    
    # Start the UDP listen thread
    udp_server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_server_sock.bind((host_ip, udp_port))
    udp_thread = threading.Thread(target=udp_listen, args=(udp_server_sock,))
    udp_thread.start()
    print(f"{GREEN}Server listening on UDP port {udp_port}{RESET}")

    # Start the TCP listen thread
    tcp_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server_sock.bind((host_ip, tcp_port))
    tcp_server_sock.listen(20)
    tcp_thread = threading.Thread(target=tcp_listen, args=(tcp_server_sock,))
    tcp_thread.start()
    print(f"{GREEN}Server listening on TCP port {tcp_port}{RESET}")

    # shutdown handle
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"{YELLOW}Server shutting down...{RESET}")
        shutdown_event.set()  # Signal threads to stop
    finally:
        print(f"{YELLOW}Cleaning up resources...{RESET}")
        broadcast_sock.close()
        udp_server_sock.close()
        tcp_server_sock.close()
        broadcast_thread.join()
        udp_thread.join()
        tcp_thread.join()
        print(f"{GREEN}Server stopped gracefully.{RESET}")

if __name__ == "__main__":
    server()

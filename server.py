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

# Offer variables
MAGIC_COOKIE = 0xabcddcba
MESSAGE_TYPE = 0x2

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
            MESSAGE_TYPE,
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
            threading.Thread(target=handle_tcp_client, args=(conn, addr, 1024 * 1024)).start()
    except OSError:
        print(f"{RED}TCP thread stopped.{RESET}")

"""
Still need to refine
"""
def handle_tcp_client(conn, addr, file_size):
    print(f"{CYAN}TCP connection established with {addr}{RESET}")
    data = str(file_size).encode() + b'\n'
    conn.sendall(data)  # Send the file size followed by a line break

    # Simulate sending the requested amount of bytes
    conn.sendall(b'A' * file_size)
    print(f"{GREEN}TCP: Sent {file_size} bytes to {addr}{RESET}")
    conn.close()

"""
Like the tcp listen, but udp doesn't have connections
"""
def udp_listen(udp_server_sock):
    try:
        while not shutdown_event.is_set():
            data, addr = udp_server_sock.recvfrom(1024)
            threading.Thread(target=handle_udp_client, args=(data, addr, 1024 * 1024)).start()
    except OSError:
        print(f"{RED}UDP thread stopped.{RESET}")

"""
also need to refine
"""
def handle_udp_client(sock, client_addr, file_size):
    print(f"{CYAN}UDP connection established with {client_addr}{RESET}")
    num_packets = file_size // 1024  # Each packet is 1024 bytes
    sent_packets = 0

    for i in range(num_packets):
        packet = f"{i}".encode() + b' ' + b'A' * 1020
        sock.sendto(packet, client_addr)
        sent_packets += 1
        time.sleep(0.01)  # Simulate packet interval

    print(f"{GREEN}UDP: Sent {sent_packets} packets to {client_addr}{RESET}")

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
    udp_server_sock.bind(("localhost", udp_port))
    udp_thread = threading.Thread(target=udp_listen, args=(udp_server_sock,))
    udp_thread.start()
    print(f"{GREEN}Server listening on UDP port {udp_port}{RESET}")

    # Start the TCP listen thread
    tcp_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server_sock.bind(("localhost", tcp_port))
    tcp_server_sock.listen(20)
    tcp_thread = threading.Thread(target=tcp_listen, args=(tcp_server_sock,))
    tcp_thread.start()
    print(f"{GREEN}Server listening on TCP port {tcp_port}{RESET}")

    # shutdown handle
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"{RED}\nServer shutting down...{RESET}")
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

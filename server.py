# server.py
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
        print(f"Broadcasted offer: UDP {server_udp_port}, TCP {server_tcp_port}")
        time.sleep(broadcast_interval)
    print(f"{RED}Broadcast thread stopped.{RESET}")

def tcp_listen(tcp_server_sock):
    try:
        while not shutdown_event.is_set():
            conn, addr = tcp_server_sock.accept()
            threading.Thread(target=handle_tcp_client, args=(conn, addr, 1024 * 1024)).start()
    except OSError:
        print(f"{RED}TCP thread stopped.{RESET}")

def handle_tcp_client(conn, addr, file_size):
    print(f"{CYAN}TCP connection established with {addr}{RESET}")
    data = str(file_size).encode() + b'\n'
    conn.sendall(data)  # Send the file size followed by a line break

    # Simulate sending the requested amount of bytes
    conn.sendall(b'A' * file_size)
    print(f"{GREEN}TCP: Sent {file_size} bytes to {addr}{RESET}")
    conn.close()

def udp_listen(udp_server_sock):
    try:
        while not shutdown_event.is_set():
            data, addr = udp_server_sock.recvfrom(1024)
            threading.Thread(target=handle_udp_client, args=(data, addr, 1024 * 1024)).start()
    except OSError:
        print(f"{RED}UDP thread stopped.{RESET}")

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

def server(udp_port=12345, tcp_port=12346):
    host_ip = socket.gethostbyname(socket.gethostname())
    print(f"{CYAN}Server started, listening on IP address {host_ip}{RESET}")
    
    # Start the offer broadcast thread
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_thread = threading.Thread(target=broadcast_offer, args=(broadcast_sock, udp_port, tcp_port), daemon=True)
    broadcast_thread.start()
    
    udp_server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_server_sock.bind(("localhost", udp_port))
    udp_thread = threading.Thread(target=udp_listen, args=(udp_server_sock,))
    udp_thread.start()
    print(f"Server listening on UDP port {udp_port}")

    tcp_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server_sock.bind(("localhost", tcp_port))
    tcp_server_sock.listen(20)
    tcp_thread = threading.Thread(target=tcp_listen, args=(tcp_server_sock,))
    tcp_thread.start()
    print(f"Server listening on TCP port {tcp_port}")

    # shutdown handle
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"{RED}\nServer shutting down...{RESET}")
        shutdown_event.set()  # Signal threads to stop
    finally:
        print(f"{CYAN}Cleaning up resources...{RESET}")
        broadcast_sock.close()
        udp_server_sock.close()
        tcp_server_sock.close()
        broadcast_thread.join()
        udp_thread.join()
        tcp_thread.join()
        print(f"{GREEN}Server stopped gracefully.{RESET}")

if __name__ == "__main__":
    server()

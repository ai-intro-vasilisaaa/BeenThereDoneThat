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
PACKET_SIZE = 1024
HEADER_SIZE = 21
PAYLOAD_SIZE = PACKET_SIZE - HEADER_SIZE
"""
Listen for broadcast offer messages from servers and return server information

Returns:
    tuple: A tuple containing the server's IP address, UDP port, and TCP port.

Raises:
    Prints a message if an invalid or corrupted offer is received.
"""
def listen_for_offer():
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client_sock.bind(("", 37020))  # Bind to listen for broadcasts on port 37020
    print(f"{YELLOW}Listening for offer requests...{RESET}")
    while True:
        data, addr = client_sock.recvfrom(PACKET_SIZE)
        if len(data) == 9:   # Expected length of offer message
            magic_cookie, offer_message_type, udp_port, tcp_port = struct.unpack('!LBHH', data[:9]) # decode data
            if magic_cookie == MAGIC_COOKIE and offer_message_type == OFFER_MESSAGE_TYPE:
                print(f"{GREEN}Received offer from {addr[0]}: UDP {udp_port}, TCP {tcp_port}{RESET}")
                client_sock.close()
                return addr[0], udp_port, tcp_port
            else:
                print(f"{RED}Invalid message received from {addr}!{RESET}")


"""
Handles TCP file transfer from the server.

Params:
    server_ip (str): The server's IP address.
    server_port (int): The server's TCP port.
    file_size (int): The size of the file to be requested in bytes.
Returns:
    None
    """
def tcp_client(server_ip, server_port, file_size):
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, server_port))

    # Send request message
    file_size_encoded = f"{file_size}\n".encode()
    header = struct.pack('!LB', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE)
    sock.sendall(header + file_size_encoded)

    # Receive payload message
    start_time = time.time()

    header = sock.recv(5)  # receive 5 bytes header
    if not header:
        print(f"{RED}Connection closed by server{RESET}")
        sock.close()
        return
    magic_cookie, message_type = struct.unpack('!LB', header)
    if magic_cookie != MAGIC_COOKIE or message_type != PAYLOAD_MESSAGE_TYPE:
        print(f"{RED}Invalid message received!\nmagic cookie - {magic_cookie}\nmessage type - {message_type}{RESET}")
        sock.close()
        return
    # Start receiving stream until needed size reached
    data = bytearray()
    while len(data) < int(file_size):
        packet = sock.recv(int(file_size) - len(data))
        if not packet:  # If connection is closed, stop receiving
            print(f"{RED}Connection closed by server{RESET}")
            sock.close()
            return
        data.extend(packet)
    bytes_received = len(data)

    end_time = time.time()

    # Calculate transfer metrics
    total_time = end_time - start_time
    total_size_bits = bytes_received * 8  # Convert bytes to bits
    speed = total_size_bits / total_time if total_time > 0 else 0

    # Print results
    print(f"{GREEN}TCP transfer finished{RESET}\ntotal time: {total_time:.2f} seconds\ntotal speed: {speed:.2f} bits/second")

    sock.close()

"""
    Handles UDP file transfer from the server.

    Args:
        server_ip (str): The server's IP address.
        server_port (int): The server's UDP port.
        file_size (int): The size of the file to be requested in bytes.
"""
def udp_client(server_ip, server_port, file_size):
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 0))
    sock.settimeout(1.0)  # Set timeout for detecting transfer end

    # Send request message
    header = struct.pack('!LBQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, int(file_size))
    sock.sendto(header, (server_ip, server_port))

    start_time = time.time()
    total_data = b""
    current_segment_count = 0
    total_segment_count = 0
    while True:
        try:
            payload_message = sock.recv(1024)  
            if not payload_message:
                break
            header = payload_message[:HEADER_SIZE]  # receive 21 bytes header
            payload = payload_message[HEADER_SIZE:]  # receive payload
            magic_cookie, message_type,total_segment_count, current_segment_count = struct.unpack('!LBQQ', header)
            if magic_cookie != MAGIC_COOKIE or message_type != PAYLOAD_MESSAGE_TYPE:
                print(f"{RED}Invalid message received!{RESET}")
                break
            total_data += payload
            if current_segment_count == total_segment_count:
                break
        except socket.timeout: # if no data is received for 1 second, transfer is done, all packets sent or no                current_segment_count += 1
                break
    end_time = time.time()

    # Handle edge cases for no data received
    if total_segment_count == 0:
        print("No data received. Transfer failed.")
        return
    # Calculate transfer metrics
    total_time = end_time - start_time
    total_size_bits = len(total_data) * 8  # Convert bytes to bits
    speed = total_size_bits / total_time if total_time > 0 else 0
    success_rate = (current_segment_count + 1) / (total_segment_count+1) * 100

    # Print results
    print(f"{GREEN}UDP transfer finished, total time: {total_time:.2f} seconds, total speed: {speed:.2f} bits/second, percentage of packets received successfully: {success_rate:.2f}{RESET}")
    sock.close()



"""
Validates and converts a user-provided connection number into Int.

Args:
    None
Returns:
    int: number of X connections
"""
def validate_conn_input(message):
    connections = input(message)
    while connections.isnumeric() == False:
        print("Invalid input. Please enter a positive Intager.")
        connections = input(message)
    return int(connections)

"""
Validates and converts a user-provided file size string into bytes.

Args:
    input_str (str): The file size as a string.

Returns:
    int: File size in bytes, number of tcp connections, number of udp connections.
"""
def validate_file_size_input():

    file_size_message = '''Enter the file size. Available formats:
        - "1TB" or "1 TB" 
        - "1GB" or "1 GB"
        - "2300MB" or "2300 MB"
        - "1024KB" or "1024 KB"
        - "123456B" or "123456"\n'''
    units = {"KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4, "B": 1}
    
    input_file_size = input(file_size_message)
    input_file_size = input_file_size.strip().upper().replace(" ", "")
    # Check if the string ends with any of the units
    while True:
        for unit, multiplier in units.items():
            if input_file_size.endswith(unit):
                try:
                    number = int(input_file_size[:-len(unit)])
                    return number * multiplier
                except ValueError:
                    print(f"Invalid size or unit: {input_file_size}")
                    break
        # Otherwise assume Bytes
        if input_file_size.isnumeric():
            return int(input_file_size)
        input_file_size = input("Enter file size: ").strip().upper()



"""
The main client function.
First receives an offer, and then receives info from user
(or maybe the opposite?)
And then sends the requests to the server, and receives payload data according to user request and shows network statistics
"""
def client_main():
    print(f"{CYAN}Client started!{RESET}")
    file_size = validate_file_size_input()
    tcp_connections = validate_conn_input("Enter the number of TCP connections: ")
    udp_connections = validate_conn_input("Enter the number of UDP connections: ")

    server_ip, server_udp_port, server_tcp_port = listen_for_offer()

    print(f"{CYAN}Starting TCP and UDP transfers...{RESET}")
    for _ in range(tcp_connections):
        threading.Thread(target=tcp_client, args=(server_ip, server_tcp_port, file_size)).start()

    for _ in range(udp_connections):
        threading.Thread(target=udp_client, args=(server_ip, server_udp_port, file_size)).start()

if __name__ == "__main__":
    client_main()

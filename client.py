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
    ## asked for no while - am thinking of a way to make it so that it listens for a certain amount of time instead of forever
    while True:
        data, addr = client_sock.recvfrom(1024)
        if len(data) == 9:   # Expected length of offer message
            magic_cookie, offer_message_type, udp_port, tcp_port = struct.unpack('!LBHH', data[:9]) # decode data
            if magic_cookie == MAGIC_COOKIE and offer_message_type == OFFER_MESSAGE_TYPE:
                print(f"{GREEN}Received offer from {addr[0]}: UDP {udp_port}, TCP {tcp_port}{RESET}")
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
    file_size_encoded = str(file_size).encode() + b'\n'
    request_message = struct.pack('!LBQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, file_size_encoded)
    sock.sendall(request_message)

    # Receive payload message
    start_time = time.time()

    total_data = b""
    while True:
        header = sock.recv(20)  # recieve 20 bytes  header
        if not header:
            break
        magic_cookie, message_type, total_segment_count, current_segment_count = struct.unpack('!LBQQ', header)
        if magic_cookie != MAGIC_COOKIE or message_type != PAYLOAD_MESSAGE_TYPE:
            print(f"{RED}Invalid message received!{RESET}")
            break
        
        data = sock.recv(1024)  # Receive payload
        if not data:  # If connection is closed, stop receiving
            break
        total_data += data
        if current_segment_count == total_segment_count:
            break
        print(f"{GREEN}Received segment {current_segment_count}/{total_segment_count}{RESET}")

    print(f"{GREEN}TCP transfer completed. Received {current_segment_count} segments.{RESET}")

    end_time = time.time()

    # Calculate transfer metrics
    total_time = end_time - start_time
    total_size_bits = len(total_data) * 8  # Convert bytes to bits
    speed = total_size_bits / total_time if total_time > 0 else 0

    # Print results
    print(f"{GREEN}TCP transfer finished, total time: {total_time:.2f} seconds, total speed: {speed:.2f} bits/second{RESET}")

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
    sock.bind((server_ip, server_port))
    sock.settimeout(1.0)  # Set timeout for detecting transfer end

    # Send request message
    file_size_encoded = str(file_size).encode() + b'\n'
    request_message = struct.pack('!LBQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, file_size_encoded)
    sock.sendall(request_message)

    start_time = time.time()

    while True:
        try:
            header = sock.recv(20)  # 20 bytes for header
            if not header:
                break
            magic_cookie, message_type, total_segment_count, current_segment_count = struct.unpack('!LBQQ', header)
            if magic_cookie != MAGIC_COOKIE or message_type != PAYLOAD_MESSAGE_TYPE:
                print(f"{RED}Invalid message received!{RESET}")
                break
            data = sock.recv(1024)  # Receive payload
            if not data:  # If connection is closed, stop receiving
                break
            total_data += data
            if current_segment_count == total_segment_count:
                break
            print(f"{GREEN}Received segment {current_segment_count}/{total_segment_count}{RESET}")
        except socket.timeout:
            i = current_segment_count + 1
            print(f"{RED}Packet {i} was lost{RESET}")

    end_time = time.time()

    # Calculate transfer metrics
    total_time = end_time - start_time
    total_size_bits = len(total_data) * 8  # Convert bytes to bits
    speed = total_size_bits / total_time if total_time > 0 else 0
    success_rate = (current_segment_count / total_segment_count) * 100

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
# def validate_file_size_input():

    file_size_message = '''
    Enter the file size. 
    Available formats: B/KB/MB/GB\n'''
    units = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}
    
#     input_file_size = input(file_size_message)
#     input_file_size = input_file_size.strip().upper()
#     # Check if the string ends with any of the units
#     while True:
#         for unit, multiplier in units.items():
#             if input_file_size.endswith(unit):
#                 try:
#                     number = int(input_file_size[:-len(unit)])
#                     return number * multiplier
#                 except ValueError:
#                     print(f"Invalid size: {input_file_size}")
#         print(f"Invalid unit. Please enter a valid unit.")
#         input_file_size = input("Enter file size: ").strip().upper()



"""
The main client function.
First receives an offer, and then receives info from user
(or maybe the opposite?)
And then sends the requests to the server, and receives payload data according to user request and shows network statistics
"""
def client_main():
    print(f"{CYAN}Client started!{RESET}")
    file_size = input("Enter the file size: ")
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

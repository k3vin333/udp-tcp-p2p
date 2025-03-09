"""
PyMesh Coordination Server

This module implements the coordination server functionality of the PyMesh P2P network.
It manages network state and coordinates peer activities using UDP protocol for all
control messages.

Key Responsibilities:
- Session management and authentication
- Network state tracking through heartbeat mechanism
- File index registry
- Search functionality for shared files
- Peer discovery and coordination

Usage:
    python server.py <port_number>

The server maintains several data structures:
1. credentials: Username/password pairs for authentication
2. activeUsers: Currently online peers and their status
3. filesUploaded: Registry of shared files and their locations
"""

from socket import *
import sys
from datetime import datetime
import time
import json
import os
import traceback

if len(sys.argv) != 2:
    print("\n===== Error: Usage: python server.py SERVER_PORT ======\n")
    exit(0)

# Network configuration
serverHost = "127.0.0.1"
serverPort = int(sys.argv[1])
serverAddress = (serverHost, serverPort)

# UDP socket for control messages
serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(serverAddress)

# Core data structures
credentials = {}  # Stores user authentication data
activeUsers = {}  # Tracks online peers and their status
filesUploaded = {}  # Maintains file sharing registry

# Load authentication data
try:
    # First try to read from the server subdirectory
    with open('server/credentials.txt', 'r') as file:
        for line in file:
            username, password = line.strip().split(' ', 1)
            credentials[username] = password.rstrip()
    print("Credentials loaded successfully from server/credentials.txt")
except FileNotFoundError:
    try:
        # Fall back to the current directory
        with open('credentials.txt', 'r') as file:
            for line in file:
                username, password = line.strip().split(' ', 1)
                credentials[username] = password.rstrip()
        print("Credentials loaded successfully from credentials.txt")
    except FileNotFoundError:
        print("Error: credentials.txt not found in either the current directory or server/")
        print("Please ensure credentials.txt exists in either location")
        exit(1)
    except Exception as e:
        print(f"Error loading credentials: {e}")
        exit(1)
except Exception as e:
    print(f"Error loading credentials: {e}")
    exit(1)

# For debugging
print(f"Server starting on port {serverPort}")
print(f"Current working directory: {os.getcwd()}")
print(f"Available credentials: {list(credentials.keys())}")

def get_timestamp():
    """Returns current timestamp in formatted string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def process_authentication(message, clientAddress):
    """
    Processes user authentication requests.
    
    Args:
        message (dict): The authentication message containing username and password
        clientAddress (tuple): The client's address (host, port)
    """
    try:
        username = message.get('username')
        password = message.get('password')
        tcpPort = message.get('tcpPort')

        print(f"{get_timestamp()}: Authentication attempt from {clientAddress} - Username: {username}")
        
        # Debug info
        print(f"Credentials check: Username exists: {username in credentials}")
        if username in credentials:
            print(f"Password check: {password} vs {credentials[username]}")
            print(f"Password matches: {credentials[username] == password}")

        if username in activeUsers:
            status = "ERROR: User already logged in"
            print(f"Authentication failed: User already logged in")
        elif username not in credentials:
            status = "ERROR: Username not found"
            print(f"Authentication failed: Username not found")
        elif credentials[username] != password:
            status = "ERROR: Incorrect password"
            print(f"Authentication failed: Incorrect password")
        else:
            activeUsers[username] = (clientAddress, time.time(), tcpPort)
            status = "OK"
            print(f"Authentication successful for {username}")
            
        print(f"Sending response: '{status}' to {clientAddress}")
        serverSocket.sendto(status.encode(), clientAddress)
        print(f"{get_timestamp()}: {clientAddress} Sent {status} to {username}")
    except Exception as e:
        print(f"Exception in authentication: {e}")
        traceback.print_exc()
        try:
            status = f"ERROR: Server error - {str(e)}"
            serverSocket.sendto(status.encode(), clientAddress)
        except:
            pass

def list_active_peers(message, clientAddress):
    """Lists all currently active peers except the requesting peer"""
    username = message.get('username')
    activePeers = [peer for peer in activeUsers.keys() if peer != username]

    if activePeers:
        res = f"{len(activePeers)} active peers:\n" + "\n".join(activePeers)
    else:
        res = "No active peers"
    
    serverSocket.sendto(res.encode(), clientAddress)
    print(f"{get_timestamp()}: {clientAddress} Sent OK to {username}")

def list_shared_files(message, clientAddress):
    """Lists all files shared by the requesting peer"""
    username = message.get('username')
    sharedFiles = [
        filename for filename, users in filesUploaded.items()
        if username in users
    ]

    if sharedFiles:
        res = f"{len(sharedFiles)} file shared:\n" + "\n".join(sharedFiles)
    else:
        res = "No files shared"

    serverSocket.sendto(res.encode(), clientAddress)
    print(f"{get_timestamp()}: {clientAddress} Sent OK to {username}")

def share_file(message, clientAddress):
    """Registers a new shared file in the network"""
    username = message.get('username')
    filename = message.get('filename')

    if filename not in filesUploaded:
        filesUploaded[filename] = []

    if username not in filesUploaded[filename]:
        filesUploaded[filename].append(username) 

    res = "File shared successfully"
    serverSocket.sendto(res.encode(), clientAddress)
    print(f"{get_timestamp()}: {clientAddress} Sent OK to {username}")

def search_files(message, clientAddress):
    """Searches for files matching the given pattern"""
    username = message.get('username')
    pattern = message.get('filename')

    matches = []
    for filename in filesUploaded:
        if pattern in filename:
            for sharer in filesUploaded[filename]:
                if sharer in activeUsers and sharer != username:
                    matches.append(filename)
                    break

    if matches:
        res = f"{len(matches)} files found:\n" + "\n".join(matches)
    else:
        res = "No files found"

    serverSocket.sendto(res.encode(), clientAddress)
    print(f"{get_timestamp()}: {clientAddress} Sent OK to {username}")

def remove_shared_file(message, clientAddress):
    """Removes a file from the shared files registry"""
    username = message.get('username')
    filename = message.get('filename')

    if filename in filesUploaded and username in filesUploaded[filename]:
        filesUploaded[filename].remove(username)

        if not filesUploaded[filename]:
            del filesUploaded[filename]

        res = "File successfully removed from sharing"
    else:
        res = "File removal failed"

    serverSocket.sendto(res.encode(), clientAddress)
    print(f"{get_timestamp()}: {clientAddress} Sent OK to {username}")

def process_fetch_request(message, clientAddress):
    """Processes a file download request"""
    username = message.get('username')
    filename = message.get('filename')

    if filename in filesUploaded:
        for sharer in filesUploaded[filename]:
            if sharer in activeUsers and sharer != username:
                sharerAddress, _, sharerPort = activeUsers[sharer]
                res = {
                    'username': sharer,
                    'address': sharerAddress[0],
                    'port': sharerPort
                }
                serverSocket.sendto(json.dumps(res).encode(), clientAddress)
                print(f"{get_timestamp()}: {clientAddress} Sent OK to {username}")
                return
    
    res = "File not found"
    serverSocket.sendto(res.encode(), clientAddress)
    print(f"{get_timestamp()}: {clientAddress} Sent ERROR to {username}")

# Main server loop
while True:
    data, clientAddress = serverSocket.recvfrom(1024)
    message = json.loads(data.decode())

    if message['type'] == 'AUTH':
        process_authentication(message, clientAddress)
    elif message['type'] == 'STATUS':
        username = message.get('username')
        if username in activeUsers:
            activeUsers[username] = (clientAddress, time.time(), activeUsers[username][2])
            print(f"{get_timestamp()}: {clientAddress} Received status update from {username}")
    elif message['type'] == 'LIST_PEERS':
        list_active_peers(message, clientAddress)
    elif message['type'] == 'LIST_FILES':
        list_shared_files(message, clientAddress)
    elif message['type'] == 'SHARE':
        share_file(message, clientAddress)
    elif message['type'] == 'SEARCH':
        search_files(message, clientAddress)
    elif message['type'] == 'REMOVE':
        remove_shared_file(message, clientAddress)   
    elif message['type'] == 'FETCH':
        process_fetch_request(message, clientAddress)
        
    # Clean up inactive peers
    currentTime = time.time()
    inactivePeers = [
        username for username, (_, last_status, _) in activeUsers.items()
        if currentTime - last_status > 3
    ]
    for username in inactivePeers:
        del activeUsers[username]
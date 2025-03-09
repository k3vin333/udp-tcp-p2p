"""
PyMesh Peer Node

This module implements the peer node functionality of the PyMesh P2P network.
It handles both UDP communication with the coordination server and TCP
connections with other peers for file transfer.

Features:
- Authentication with coordination server
- Network presence through heartbeat mechanism
- File sharing and discovery
- Direct peer-to-peer file transfer
- Concurrent transfer handling

Usage:
    python client.py <server_port>

The peer node maintains two types of connections:
1. UDP connection with coordinator for control messages
2. TCP connections with peers for file transfer
"""

import json
import socket
from socket import *
import sys
import threading
import time
import os
import traceback

if len(sys.argv) != 2:
    print("\n===== Error: Usage: python client.py SERVER_PORT ======\n")
    exit(0)

# Network configuration
serverHost = "127.0.0.1"
serverPort = int(sys.argv[1])
serverAddress = (serverHost, serverPort)

# UDP socket for coordinator communication
clientSocket = socket(AF_INET, SOCK_DGRAM)

# TCP socket for peer file transfer
tcpSock = socket(AF_INET, SOCK_STREAM)
tcpSock.bind(('127.0.0.1', 0))
tcpPort = tcpSock.getsockname()[1]

tcpSock.listen()

# Session state
username = None
authenticated = False

def send_heartbeat():
    """Sends periodic heartbeat to maintain connection with coordinator"""
    while authenticated:
        statusMsg = {
            'type': 'STATUS',
            'username': username
        }
        clientSocket.sendto(json.dumps(statusMsg).encode(), serverAddress)
        time.sleep(2)

def handle_incoming_transfers():
    """Handles incoming file transfer connections from peers"""
    while authenticated:
        clientSocket, _ = tcpSock.accept()
        transferThread = threading.Thread(target=process_transfer_request, args=(clientSocket,))
        transferThread.daemon = True
        transferThread.start()

def process_transfer_request(clientSocket):
    """Processes an incoming file transfer request"""
    try:
        # Set a timeout for receiving the initial request
        clientSocket.settimeout(5)
        
        data = clientSocket.recv(1024)
        if not data:
            print("Error: Received empty request")
            clientSocket.close()
            return
            
        request = json.loads(data.decode())
        filename = request['filename']
        requester = request['username']
        
        print(f"Received file request from {requester} for {filename}")

        # Use global username variable to determine the current user's directory
        global username
        
        # The current user should look in their own directory for the file to share
        userDir = f"./{username}/"  # Current user's directory
        filePath = os.path.join(userDir, filename)
        print(f"Looking for file at: {filePath}")

        # Check if file exists
        if not os.path.exists(filePath):
            print(f"Error: File not found at {filePath}")
            clientSocket.close()
            return

        try:
            # Get and send file size
            fileSize = os.path.getsize(filePath)
            print(f"File size: {fileSize} bytes. Sending to requester...")
            clientSocket.sendall(str(fileSize).encode())
            
            # Wait for acknowledgment
            print("Waiting for acknowledgment...")
            ack = clientSocket.recv(1024)
            if ack != b'ACK':
                print(f"Error: Expected ACK but received {ack}")
                clientSocket.close()
                return
                
            print("Acknowledgment received. Sending file...")
            
            # Send the file
            with open(filePath, 'rb') as file:
                # Send in chunks
                bytesRead = 0
                while True:
                    fileData = file.read(1024)
                    if not fileData:
                        break
                    clientSocket.sendall(fileData)
                    bytesRead += len(fileData)
                    percent = min(100, int((bytesRead / fileSize) * 100))
                    print(f"Upload progress: {percent}%", end="\r")
            
            print(f"\nFile {filename} sent successfully to {requester}")
        except Exception as e:
            print(f"Error sending file: {e}")
    except json.JSONDecodeError:
        print("Error: Invalid JSON in request")
    except Exception as e:
        print(f"Error processing transfer request: {e}")
    finally:
        clientSocket.close()

# Start transfer handler thread
transferThread = threading.Thread(target=handle_incoming_transfers)
transferThread.daemon = True
transferThread.start()

# Set socket timeout to prevent hanging
clientSocket.settimeout(5)  # 5 second timeout for UDP socket

# Main client loop
print("=== PyMesh P2P Client ===")
print("Connecting to server at {}:{}".format(serverHost, serverPort))

while True:
    if not authenticated:
        username = input("Enter username: ")
        password = input("Enter password: ")

        try:
            authMsg = {
                'type': 'AUTH',
                'username': username,
                'password': password,
                'tcpPort': tcpPort
            }

            print(f"Sending authentication request for user {username}...")
            clientSocket.sendto(json.dumps(authMsg).encode(), serverAddress)
            
            try:
                print("Waiting for server response...")
                authMsg, _ = clientSocket.recvfrom(1024)
                res = authMsg.decode()
                print(f"Received response: {res}")

                if res == "OK":
                    authenticated = True
                    print("Authentication successful!")
                    print("Welcome to PyMesh P2P Network!")
                    print("Available commands:")
                    print("  peers: List active peers")
                    print("  myfiles: List your shared files")
                    print("  share <filename>: Share a file")
                    print("  find <pattern>: Search for files")
                    print("  remove <filename>: Unshare a file")
                    print("  fetch <filename>: Download a file")
                    print("  quit: Exit")

                    # Create user directory if it doesn't exist
                    userDir = f"./{username}/"
                    if not os.path.exists(userDir):
                        os.makedirs(userDir)
                        print(f"Created directory: {userDir}")

                    heartbeatThread = threading.Thread(target=send_heartbeat)
                    heartbeatThread.daemon = True
                    heartbeatThread.start()
                    print("Status update thread started")
                else:
                    print(f"Authentication failed: {res}")
                    continue
            except socket.timeout:
                print("Error: Server did not respond to authentication request")
                print("Make sure the server is running and try again")
                continue
            except Exception as e:
                print(f"Error during authentication: {e}")
                traceback.print_exc()
                continue
        except Exception as e:
            print(f"Error preparing authentication: {e}")
            continue
    else:
        command = input("> ")
        cmdPrefix = command[:5] if len(command) >= 5 else command

        if command == "peers":
            peerMsg = {
                'type': 'LIST_PEERS',
                'username': username
            }
            clientSocket.sendto(json.dumps(peerMsg).encode(), serverAddress)
            res, _ = clientSocket.recvfrom(1024)
            print(res.decode())

        elif command == "myfiles":
            filesMsg = {
                'type': 'LIST_FILES',
                'username': username
            }
            clientSocket.sendto(json.dumps(filesMsg).encode(), serverAddress)
            res, _ = clientSocket.recvfrom(1024)
            print(res.decode())

        elif cmdPrefix == "share":
            filename = command[6:]
            userDir = f"./{username}/"
            filePath = os.path.join(userDir, filename)
            
            if not os.path.exists(filePath):
                print("File not found")
                continue

            shareMsg = {
                'type': 'SHARE',
                'username': username,
                'filename': filename
            }
            clientSocket.sendto(json.dumps(shareMsg).encode(), serverAddress)
            res, _ = clientSocket.recvfrom(1024)
            print(res.decode())

        elif cmdPrefix == "find":
            pattern = command[5:]
            searchMsg = {
                'type': 'SEARCH',
                'username': username,
                'filename': pattern
            }
            clientSocket.sendto(json.dumps(searchMsg).encode(), serverAddress)
            res, _ = clientSocket.recvfrom(1024)
            print(res.decode())

        elif cmdPrefix == "remove":
            filename = command[7:]
            removeMsg = {
                'type': 'REMOVE',
                'username': username,
                'filename': filename
            }
            clientSocket.sendto(json.dumps(removeMsg).encode(), serverAddress)
            res, _ = clientSocket.recvfrom(1024)
            print(res.decode())

        elif cmdPrefix == "fetch":
            filename = command[6:]
            fetchMsg = {
                'type': 'FETCH',
                'username': username,
                'filename': filename
            }
            
            try:
                clientSocket.sendto(json.dumps(fetchMsg).encode(), serverAddress)
                res, _ = clientSocket.recvfrom(1024)
                response = res.decode()

                userDir = f"./{username}/"
                
                # Create user directory if it doesn't exist
                if not os.path.exists(userDir):
                    os.makedirs(userDir)
                    print(f"Created directory {userDir}")

                if response != "File not found":
                    try:
                        peerInfo = json.loads(response)
                        print(f"Connecting to peer at {peerInfo['address']}:{peerInfo['port']}...")
                        
                        # Setup timeout to avoid hanging
                        transferSocket = socket(AF_INET, SOCK_STREAM)
                        transferSocket.settimeout(10)  # 10 second timeout
                        
                        try:
                            transferSocket.connect((peerInfo['address'], peerInfo['port']))
                            print("Connected to peer. Requesting file...")
                            
                            # Send file request
                            request = {
                                'username': username,
                                'filename': filename
                            }
                            transferSocket.send(json.dumps(request).encode())
                            print("Request sent. Waiting for file size...")
                            
                            # Receive file size with timeout
                            try:
                                fileSizeData = transferSocket.recv(1024)
                                if not fileSizeData:
                                    print("Error: Received empty file size response from peer")
                                    return
                                    
                                fileSize = int(fileSizeData.decode())
                                print(f"File size: {fileSize} bytes. Sending acknowledgment...")
                                transferSocket.send(b'ACK')
                                
                                print("Receiving file...")
                                with open(os.path.join(userDir, filename), 'wb') as file:
                                    received = 0
                                    while received < fileSize:
                                        data = transferSocket.recv(1024)
                                        if not data:
                                            break
                                        file.write(data)
                                        received += len(data)
                                        # Show progress
                                        percent = min(100, int((received / fileSize) * 100))
                                        print(f"Download progress: {percent}%", end="\r")
                            
                                print(f"\n{filename} downloaded successfully")
                            except socket.timeout:
                                print("Error: Timed out waiting for file size from peer")
                            except ValueError as e:
                                print(f"Error: Invalid file size received: {e}")
                        except socket.timeout:
                            print("Error: Timed out connecting to peer")
                        except ConnectionRefusedError:
                            print(f"Error: Connection refused by peer at {peerInfo['address']}:{peerInfo['port']}")
                        except Exception as e:
                            print(f"Error during connection: {e}")
                        finally:
                            transferSocket.close()
                    except json.JSONDecodeError as e:
                        print(f"Error parsing peer info: {e}")
                    except KeyError as e:
                        print(f"Error: Missing field in peer info - {e}")
                    except Exception as e:
                        print(f"Error processing peer connection: {e}")
                else:
                    print(response)
            except Exception as e:
                print(f"Error during fetch operation: {e}")
                traceback.print_exc()

        elif command == "quit":
            print("Goodbye!")
            break
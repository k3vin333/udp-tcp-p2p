# Distributed P2P File Sharing Network

A distributed peer-to-peer file sharing system implemented in Python that leverages both UDP and TCP protocols for efficient and reliable file transfer. This project demonstrates a hybrid architecture combining centralized coordination with decentralized file transfer.

## Architecture Overview

The system consists of three main components:

1. **Coordination Server (`server.py`)**
   - Manages user sessions and authentication
   - Maintains network state through status updates
   - Coordinates file discovery and sharing
   - Uses UDP for lightweight control messages

2. **Peer Node (`client.py`)**
   - Provides CLI for network operations
   - Implements hybrid UDP/TCP communication
   - Supports file indexing and transfer
   - Maintains network presence through status updates

3. **Direct Transfer Protocol**
   - Peer-to-peer TCP file transfer
   - Optimized large file handling
   - Multi-session transfer support

## Features

- **Secure Authentication**: Username/password based access control
- **Network State Management**: Real-time peer availability tracking
- **File Indexing**: Distributed file sharing system
- **File Discovery**: Network-wide file search capabilities
- **P2P Transfer**: Direct peer-to-peer file transfer using TCP
- **Concurrent Operations**: Multiple simultaneous transfer support
- **Robust Error Handling**: Comprehensive network error management

## Technical Implementation

### Protocol Design

1. **UDP Protocol (Control Layer)**
   - Session management (`AUTH`)
   - Network state updates (`STATUS`)
   - File operations (`SHARE`, `REMOVE`)
   - Peer discovery (`LIST_PEERS`, `LIST_FILES`, `SEARCH`)

2. **TCP Protocol (Transfer Layer)**
   - Reliable file transfer
   - Streaming transfer support
   - Session management

### Data Structures

- Session management store
- Network state tracker
- File index registry
- Transfer session manager

## Setup and Usage

1. **Prerequisites**
   ```
   Python 3.x
   ```

2. **Starting the Coordination Server**
   ```
   python server.py <port_number>
   ```

3. **Starting a Peer Node**
   ```
   python client.py <server_port>
   ```

## Available Commands

- **Network Operations**:
  - `peers`: List active peers in the network
  - `myfiles`: List your shared files
  - `share <filename>`: Share a file with the network
  - `find <pattern>`: Search for files by pattern
  - `remove <filename>`: Stop sharing a file
  - `fetch <filename>`: Download a file from a peer
  - `quit`: Exit the network

## Network Architecture

```
+-------------+         UDP         +--------------+
|             |<------------------>|   Peer 1     |
| Coordinator |                    |              |
|   Server    |         UDP        +--------------+
|             |<------------------>|   Peer 2     |
| - Sessions  |                    |              |
| - Discovery |                    +--------------+
+-------------+                          |
                                        | TCP
                                        |
                                 +--------------+
                                 |   Peer 3     |
                                 |              |
                                 +--------------+
```

## Error Handling

- Network connectivity management
- Session authentication
- Transfer interruption recovery
- Peer availability tracking
- Invalid operation handling

## Future Enhancements

1. End-to-end encryption support
2. File integrity verification
3. Bandwidth optimization
4. Parallel transfer support
5. NAT traversal capabilities

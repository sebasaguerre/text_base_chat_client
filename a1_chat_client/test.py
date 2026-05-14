import socket 
import select      # for pooling 
import threading


# sending information through a socket 

# init socket 
"""
args = (Address family, Socket type)
    AF_INET = Address Family: Internet => IPv4  `this is the NETWORK-layer address`
    SOCK_STREAM  = TCP  `this is the Trasport-layer protocol`
""" 
socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connect to network
"""
IP address = computer on the internet address
Port = what program should recieve the data 
    - usually betw. 1024 and 655535
    - NOTE if you are a client you must use the same port as the server

local host -> 127.0.0.1     `check the current local computer`

"""
local_host = "127.0.0.1"
host_port = (local_host, 4321)
socket.connect(host_port)       # connect socket to network address = host = IP add + port 

# sending data over socket
"""
Data must me converted into bytes
NOTE OS determines how many bytes are send each time 
"""
byte_msg = "This is our message".encode("utf-8")      # this is the buffer 
num_bytes_to_send = len(byte_msg)

# iteratively send data
while num_bytes_to_send > 0:
    # send bytes in according to OS capacity 
    num_bytes_to_send -= socket.send(byte_msg[byte_msg - num_bytes_to_send:])


# buffer based messgae sending 
def send_msg(sock, msg):
    bmsg = msg.encode("utf-8")
    total_len = len(bmsg)
    bsent = 0 

    while bsent < total_len:
        
        # amount of data left to send 
        remaining_data = bmsg[bsent:]
        # amount of bytes sent 
        bsent_now = sock.send(remaining_data)

        if bsent_now == 0:
            raise RuntimeError("Socket connection broke")
        
        bsent += bsent_now
    
    print("Msg sent successfully")

# recieving data using a socket 
def recieve_msg(sock, msg_length):
    recieved_msg = b""

    while len(recieved_msg) < msg_length:
        msg_chunk = sock.recv(4096)    # buffer limit for recieveing at most 4096 bytes per time `rate limit`

        if not msg_chunk:
            # if empty => other side closed the connection 
            print("Connection closed by server")
            break
        
        # incrementally rebuild original msg
        recieved_msg += msg_chunk

    return recieved_msg.decode("utf-8")


"""
To avoid the 'Framing' problem (for how long should we try to recieve a msg)
we use length prefix:= sending a prefix of 4 byte with the legth of the msg
    We use the struct module and the pack function
or we use a delimiter symbol to signal the end of the msg => '\n'
For 
"""
import struct
# how to encode for length prefix 
message = "This is our msg"
data = message.encode("utf-8")

# here 'I' means unsigned 4-byte integer 
# this creates the header containing the leght 
header = struct.pack('!I',  len(data))
full_data = header + data 

# send data
send_msg(socket, full_data)

def send_mgs_wpref(sock, msg):
    # how to encode for length prefix 
    data = msg.encode("utf-8")

    # create msg with 
    header = struct.pack('!I',  len(data))
    full_data = header + data 

    # send data
    send_msg(socket, full_data)

### recieving a msg with a prefix 
def recv_msg_wpref(sock):

    # recieve prefix
    prefix = b""
    while len(prefix) < 4:
        chunck = sock.recv(4 - len(prefix))
        if not chunck: return None 
        prefix += chunck 

    # convert binary  4-bytes into integer 
    msg_len = struct.unpack("!I", prefix)[0]

    recieved_data = b""
    
    while len(recieved_data) < msg_len:

        # only ask required byte size using 4096
        bytes_to_pull = min(4096, msg_len - recieved_data )
        # current data being recieved 
        cdata = sock.recv(bytes_to_pull)

        if not cdata:
            print("Socket is closed.")
            break 

        recieved_data += cdata
    
    # return message 
    return recieved_data.decode("uft-8")

    
"""
For testing and enabling the server to restart without locking-in the port
this must be executed after you create a socket 

"""
sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#############################################################################################

"""
since networking can be "dirty" we use try and except blocks:
""" 

# Create the socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Set the REUSE flag (CRITICAL for testing)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    # Connect to the host
    sock.connect(("127.0.0.1", 4321))
    
    # Attempt to send/receive
    message = "Hello Network!".encode("utf-8")
    sock.send_msg_wpref(message) # Note: In your real code, use your while-loop for sending!
    
    answer = recv_msg_wpref(sock)

except OSError as e:
    # If the server isn't running or the connection drops, you end up here
    print(f"A networking error occurred: {e}")

finally:
    # This runs no matter what, ensuring the socket closes properly
    sock.close()

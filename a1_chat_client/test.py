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
full_data = header + header 

# send data
send_msg(socket, full_data)


### recieving a msg with a prefix 
def recv_msg_nprefix(sock):

    # read the length prefix 
    prefix_data = struct.unpack('!I', prefix_data)[0]
    msg_len = prefix_data.decode("uft-8")

    recieved_data = b""
    
    while len(recieved_data) < msg_len:

        # current data being recieved 
        cdata = sock.recv(4096)

        if not cdata:
            print("Socket is closed.")
            break 

        recieved_data += cdata
    
    return recieved_data.decode("uft-8")
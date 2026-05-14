from argparse import Namespace, ArgumentParser
import socket
import struct


def parse_arguments() -> Namespace:
    """
    Parse command line arguments for the chat client.
    The two valid options are:
        --address: The host to connect to. Default is "0.0.0.0"
        --port: The port to connect to. Default is 5378
    :return: The parsed arguments in a Namespace object.
    """

    parser: ArgumentParser = ArgumentParser(
        prog="python -m a1_chat_client",
        description="A1 Chat Client assignment for the VU Computer Networks course.",
        epilog="Authors: Your group name"
    )
    parser.add_argument("-a", "--address",
                      type=str, help="Set server address", default="0.0.0.0")
    parser.add_argument("-p", "--port",
                      type=int, help="Set server port", default=5378)
    return parser.parse_args()

def send_msg_wpref(sock, msg):
    
    # conver messge to binary 
    data = msg.encode("utf-8")
    # create msg with prefix
    header = struct.pack('!I',  len(data))
    prefixed_data = header + data

    total_len = len(prefixed_data)
    bsent = 0 

    # send data 
    while bsent < total_len:
        
        # amount of data left to send 
        remaining_data = prefixed_data[bsent:]
        # amount of bytes sent 
        bsent_now = sock.send(remaining_data)

        if bsent_now == 0:
            raise RuntimeError("Socket connection broke")
        
        bsent += bsent_now
    
    print("Msg sent successfully")


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



# Execute using `python -m a1_chat_client`
def main() -> None:
    args: Namespace = parse_arguments()
    port: int = args.port
    host: str = args.address

    # get username via input 
    username = input("Username: ").strip()

    # open up a socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # connect socket
    sock.connect((host, port))


  


if __name__ == "__main__":
    main()


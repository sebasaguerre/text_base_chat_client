from argparse import Namespace, ArgumentParser
import socket
import select

FORBIDDEN_CHARS = set("!@#$%^&* ")


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

def send_msg(sock, msg):
    
    # conver messge to binary 
    data = msg.encode("utf-8") + b"\n"
    total_len = len(data)
    bsent = 0 

    # send data 
    while bsent < total_len:
        
        # amount of data left to send 
        remaining_data = data[bsent:]
        # amount of bytes sent 
        bsent_now = sock.send(remaining_data)

        if bsent_now == 0:
            raise RuntimeError("Socket connection broke")
        
        bsent += bsent_now

def handle_msg(msg):
    pass

def recv_msg(sock, buffer):

    recv_data = b""
    
    while True:
        # recieve data chunck
        chunck = sock.recv(1024).decode("utf-8")

        # check if chunck is empty
        if chunck == "":
            break
        
        recieved_msg += chunck

        # check for delimiter 
        while "\n" in recv_data:
            msg, recv_data = recv_data.split("\n", 1) 
            handle_msg(msg)

def recv_line(sock, buffer):
    # recieve data until delimiter is encounterd
    while "\n" not in buffer[0]:
        chunk = sock.recv(4096)

        # check if chuck is empty
        if not chunk:
            return None 
        
        buffer[0] += chunk.decode("utf-8")
        
        # attempt to extract line from buffer
        line, buffer[0] = buffer[0].split("\n", 1)
    
    return line



def handle_server_msg(line):
    pass

def handle_user_input(sock, line):
    pass

# authentification and login functions 

def contain_forbidden_chars(name):
    "Check if usarename contains any forbidden chars"
    return any(char in FORBIDDEN_CHARS for char in name)

def login(sock, buffer):
    """
    Handle login sequence. 
    Returns True if succesful login or False otherwise
    """

    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)
    



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


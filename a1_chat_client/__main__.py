from argparse import Namespace, ArgumentParser
import socket
import select
import sys 

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
    print(f"[DEBUG] senginf raw bytes: {data!r}")

    # send data 
    while bsent < total_len:
        
        # amount of data left to send 
        remaining_data = data[bsent:]
        # amount of bytes sent 
        bsent_now = sock.send(remaining_data)

        if bsent_now == 0:
            raise RuntimeError("Socket connection broke")
        
        bsent += bsent_now
    
    print(f"[DEBUG] sent {bsent} bytes")

def recv_line(sock, buffer):

    print(f"[DEBUG] recv_line called, socket fd={sock.fileno()}")
    # recieve data until delimiter is encounterd
    while "\n" not in buffer[0]:
        chunk = sock.recv(4096)

        # check if chuck is empty
        if not chunk:
            return None 
        
        buffer[0] += chunk.decode("utf-8")
        
    # extract line from buffer
    line, buffer[0] = buffer[0].split("\n", 1)

    return line

def handle_server_msg(line):
    """
    check for every server response interpret them
    """
    if line.startswith("DELIVERY "):
        parts = line.split(" ", 2)
        if len(parts) == 3:
            print(f"From {parts[1]}: {parts[2]}")

    elif line == "SEND-OK":
        print("The message was sent succesfully")

    elif line == "BAD-DEST-USER":
        print("The destination user does not exist")

    elif line.startswith("LIST-OK "):
        user_list_str = line[len("LIST-OK "): ]
        users = user_list_str.split(",") if user_list_str else [] 
        print(f"There are {len(users)} online users: ")
        for user in users:
            print(user)

    elif line == "BAD-RQST-HDR":
        print("Error: Unknown issue in previous message header.")
 
    elif line == "BAD-RQST-BODY":
        print("Error: Unknown issue in previous message body.")
 
    return True

def handle_user_input(sock, line):
    "Parse a single line of user input and act accordingly"
    
    line = line.strip()

    # exit chat 
    if line == "!quit":
        return False
    
    # recieve list of currently active users 
    elif line == "!who":
        send_msg(sock, "LIST")
        return True 
    
    # user and message processing
    elif line.startswith("@"):
        # @[usrname] [message]
        parts = line.split(" ", 1)
        # send message 
        if len(parts) == 2:
            dest_user = parts[0][1:]
            msg = parts[1]
            send_msg(sock, f"SEND {dest_user} {msg}")
            return True 

    # ignore input that does not follow the above commands 

# authentification and login functions 

def contains_forbidden_chars(name):
    "Check if usarename contains any forbidden chars"
    return any(char in FORBIDDEN_CHARS for char in name)

def login(sock, buffer):
    """
    Handle login sequence. 
    Returns True if succesful login or False otherwise
    """

    # print("Welcome to Chat Client. Enter your login: ", end="", flush=True)

    # loop until login happens, no response or Busy
    while True:
            
            print("Welcome to Chat Client. Enter your login: ", end="", flush=True)
            username = input().strip()

            # check for forbbiden char
            if contains_forbidden_chars(username):
                print(f"Cannot log in as {username}. That username contains disallowed characters.")
                continue
            
            # send msg to server
            msg = f"HELLO-FROM {username}"
            send_msg(sock, msg)
            print(f"[DEBUG] msg being seng {msg}")
            response = recv_line(sock, buffer)
            print(f"[DEBUG] response by server recieved: {response}")

            if response is None:
                return False 
            
            # validate login 
            if response == f"HELLO {username}":
                print(f"Succefully logged in as {username}!")
                return True 
            
            # user in use
            elif response == "IN-USE":
                print(f"Cannot log in as {username}. That username is already in use.")

            # server is busy, terminate interaction
            elif response == "BUSY":
                print("Cannot log in. The server is full!")
                return False 
            
            else: 
                print(f"Cannot log in as {username}. That username contains disallowed characters.")
                

# Execute using `python -m a1_chat_client`
def main() -> None:
    args: Namespace = parse_arguments()
    port: int = args.port
    host: str = args.address

    # open up a socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # connect socket
    sock.connect((host, port))
    print(f"[DEBUG] socket fd={sock.fileno()}, peer={sock.getpeername()}, local={sock.getsockname()}")

    # buffer to monitor multiple files/interactions
    buffer = [""]

    # check if lockin is not succesful 
    if not login(sock, buffer):
        sock.close()
        return 
    
    # server-client interaction until smt fails or 
    while True:

        readable, _, _ = select.select([sock, sys.stdin], [], [])

        for fd in readable:
            
            # check file is socket 
            if fd is sock: 
                line = recv_line(sock, buffer)
                print(f"[DEBUG] raw response {line!r}")

                if line is None:
                    print("Disconnected from server.")
                    sock.close()
                    return

                # process server msg
                handle_server_msg(line)
            
            elif fd is sys.stdin:
                user_line = sys.stdin.readline()

                if not user_line:
                    sock.close()
                    return 
                
                if not handle_user_input(sock, user_line):
                    sock.close()
                    return 

    
if __name__ == "__main__":
    main()


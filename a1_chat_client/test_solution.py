from argparse import Namespace, ArgumentParser
import socket
import select
import sys
 
# @ is intentionally excluded — the server validates it, not the client
FORBIDDEN_CHARS = set("!#$%^&* ")
 
 
def parse_arguments() -> Namespace:
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
    data = msg.encode("utf-8") + b"\n"
    total_len = len(data)
    bsent = 0
 
    while bsent < total_len:
        bsent_now = sock.send(data[bsent:])
        if bsent_now == 0:
            raise RuntimeError("Socket connection broke")
        bsent += bsent_now
 
 
def recv_line(sock, buffer):
    """
    buffer[0] is a bytearray. Reads from sock until a newline is found,
    then returns the decoded line. Returns None if the connection closed.
    """
    while b"\n" not in buffer[0]:
        chunk = sock.recv(4096)
        if not chunk:
            return None
        buffer[0] += chunk
 
    idx = buffer[0].index(b"\n")
    line_bytes = buffer[0][:idx]
    buffer[0] = buffer[0][idx + 1:]
 
    return line_bytes.decode("utf-8", errors="replace")
 
 
def handle_server_msg(line):
    """Print the appropriate output for a server response line."""
 
    if line.startswith("DELIVERY "):
        parts = line.split(" ", 2)
        if len(parts) == 3:
            print(f"From {parts[1]}: {parts[2]}", flush=True)
 
    elif line == "SEND-OK":
        print("The message was sent successfully", flush=True)
 
    elif line == "BAD-DEST-USER":
        print("The destination user does not exist", flush=True)
 
    elif line.startswith("LIST-OK "):
        user_list_str = line[len("LIST-OK "):]
        users = user_list_str.split(",") if user_list_str else []
        print(f"There are {len(users)} online users: ", flush=True)
        for user in users:
            print(user, flush=True)
 
    elif line == "BAD-RQST-HDR":
        print("Error: Unknown issue in previous message header.", flush=True)
 
    elif line == "BAD-RQST-BODY":
        print("Error: Unknown issue in previous message body.", flush=True)
 
 
def handle_user_input(sock, line):
    """
    Parse a line of user input. Returns False if the client should quit.
    """
    line = line.strip()
 
    if line == "!quit":
        return False
 
    elif line == "!who":
        send_msg(sock, "LIST")
 
    elif line.startswith("@"):
        parts = line.split(" ", 1)
        dest_user = parts[0][1:]
        msg = parts[1] if len(parts) == 2 else ""
        send_msg(sock, f"SEND {dest_user} {msg}")
 
    # All other input silently ignored per spec
    return True
 
 
def contains_forbidden_chars(name):
    return any(char in FORBIDDEN_CHARS for char in name)
 
 
def login(sock, buffer):
    """
    Handle login using select() on both sock and stdin simultaneously so:
      - The prompt is printed before any blocking call
      - stdin is never frozen while waiting for the server
      - !quit works at any point during login
      - stdin lines that arrive while waiting for a server response are
        returned as a list so main() can replay them as post-login commands
 
    Returns (True, [stashed_lines]) on success, (False, []) on exit/error.
    """
    state = 'prompt'        # 'prompt' | 'await_server'
    pending_username = None
    stashed_lines = []      # stdin lines received while awaiting server reply
 
    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)
 
    while True:
        readable, _, _ = select.select([sock, sys.stdin], [], [])
 
        for fd in readable:
 
            # ── server ───────────────────────────────────────────────────
            if fd is sock:
                # Only process server data if we actually sent a HELLO-FROM
                if state != 'await_server':
                    recv_line(sock, buffer)
                    continue
 
                response = recv_line(sock, buffer)
 
                if response is None:
                    return False, []
 
                if response == f"HELLO {pending_username}":
                    print(f"Successfully logged in as {pending_username}!", flush=True)
                    return True, stashed_lines
 
                elif response == "IN-USE":
                    print(f"Cannot log in as {pending_username}. That username is already in use.", flush=True)
                    state = 'prompt'
                    pending_username = None
                    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)
 
                elif response == "BUSY":
                    print("Cannot log in. The server is full!", flush=True)
                    return False, []
 
                else:
                    # Any other server rejection (BAD-RQST-HDR, BAD-RQST-BODY, etc.)
                    print(f"Cannot log in as {pending_username}. That username contains disallowed characters.", flush=True)
                    state = 'prompt'
                    pending_username = None
                    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)
 
            # ── stdin ────────────────────────────────────────────────────
            elif fd is sys.stdin:
                raw = sys.stdin.readline()
 
                if not raw:
                    return False, []
 
                text = raw.strip()
 
                if text == "!quit":
                    return False, []
 
                if state == 'await_server':
                    # A post-login command arrived before the server replied.
                    # Stash it; main() will process it after login completes.
                    stashed_lines.append(raw)
                    continue
 
                if contains_forbidden_chars(text):
                    print(f"Cannot log in as {text}. That username contains disallowed characters.", flush=True)
                    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)
                    continue
 
                send_msg(sock, f"HELLO-FROM {text}")
                pending_username = text
                state = 'await_server'
 
 
def main() -> None:
    args: Namespace = parse_arguments()
    port: int = args.port
    host: str = args.address
 
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.connect((host, port))
 
    buffer = [b""]
 
    success, stashed_lines = login(sock, buffer)
    if not success:
        sock.close()
        return
 
    # Replay any stdin lines that arrived during the login handshake
    for line in stashed_lines:
        if not handle_user_input(sock, line):
            sock.close()
            return
 
    # Main event loop
    while True:
        readable, _, _ = select.select([sock, sys.stdin], [], [])
 
        for fd in readable:
 
            if fd is sock:
                line = recv_line(sock, buffer)
                if line is None:
                    print("Disconnected from server.", flush=True)
                    sock.close()
                    return
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
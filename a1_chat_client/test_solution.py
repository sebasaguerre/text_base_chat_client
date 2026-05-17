from argparse import Namespace, ArgumentParser
import socket
import select
import sys

FORBIDDEN_CHARS = set("!@#$%^&* ")


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
        remaining_data = data[bsent:]
        bsent_now = sock.send(remaining_data)

        if bsent_now == 0:
            raise RuntimeError("Socket connection broke")

        bsent += bsent_now


def recv_line(sock, buffer):
    """
    Read bytes from sock into buffer (a bytearray) until a newline is found.
    buffer[0] holds raw bytes. Returns a decoded string line, or None on close.
    """
    while b"\n" not in buffer[0]:
        chunk = sock.recv(4096)

        if not chunk:
            return None

        buffer[0] += chunk

    idx = buffer[0].index(b"\n")
    line_bytes = buffer[0][:idx]
    buffer[0] = buffer[0][idx + 1:]

    # errors="replace" prevents crashes on multi-byte chars split across packets
    return line_bytes.decode("utf-8", errors="replace")


def handle_server_msg(line):
    """Interpret a server response line and print the appropriate output."""

    if line.startswith("DELIVERY "):
        parts = line.split(" ", 2)
        if len(parts) == 3:
            print(f"From {parts[1]}: {parts[2]}")

    elif line == "SEND-OK":
        print("The message was sent successfully")

    elif line == "BAD-DEST-USER":
        print("The destination user does not exist")

    elif line.startswith("LIST-OK "):
        user_list_str = line[len("LIST-OK "):]
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
    """
    Parse a line of user input. Returns False if client should quit, True otherwise.
    """
    line = line.strip()

    if line == "!quit":
        return False

    elif line == "!who":
        send_msg(sock, "LIST")

    elif line.startswith("@"):
        parts = line.split(" ", 1)
        dest_user = parts[0][1:]
        # Always send even with an empty body — let the server reject with BAD-RQST-BODY
        msg = parts[1] if len(parts) == 2 else ""
        send_msg(sock, f"SEND {dest_user} {msg}")

    # Any other input is silently ignored per spec

    return True


def contains_forbidden_chars(name):
    return any(char in FORBIDDEN_CHARS for char in name)


def login(sock, buffer):
    """
    Handle login using select() on both sock and stdin so that:
      - stdin is never blocked while waiting for the server
      - !quit works before login completes
      - stdin lines that arrive during server wait are stashed for main()

    Returns True on successful login, False if we should exit.
    Any stdin lines stashed during login are appended to buffer[1:].
    """
    state = 'prompt'       # 'prompt' | 'await_server'
    pending_username = None

    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)

    while True:
        readable, _, _ = select.select([sock, sys.stdin], [], [])

        for fd in readable:

            # ── server messages ──────────────────────────────────────────
            if fd is sock:
                if state != 'await_server':
                    # Unexpected server data before we sent anything — drain it
                    recv_line(sock, buffer)
                    continue

                response = recv_line(sock, buffer)

                if response is None:
                    return False

                if response == f"HELLO {pending_username}":
                    print(f"Successfully logged in as {pending_username}!")
                    return True

                elif response == "IN-USE":
                    print(f"Cannot log in as {pending_username}. That username is already in use.")
                    state = 'prompt'
                    pending_username = None
                    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)

                elif response == "BUSY":
                    print("Cannot log in. The server is full!")
                    return False

                else:
                    print(f"Cannot log in as {pending_username}. That username contains disallowed characters.")
                    state = 'prompt'
                    pending_username = None
                    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)

            # ── stdin input ──────────────────────────────────────────────
            elif fd is sys.stdin:
                raw = sys.stdin.readline()

                if not raw:
                    return False

                username = raw.strip()

                # !quit works at any point, even before login
                if username == "!quit":
                    return False

                if state == 'await_server':
                    # A post-login command arrived before the server responded.
                    # Stash it in buffer so main() can replay it after login.
                    buffer.append(raw)
                    continue

                if contains_forbidden_chars(username):
                    print(f"Cannot log in as {username}. That username contains disallowed characters.")
                    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)
                    continue

                send_msg(sock, f"HELLO-FROM {username}")
                pending_username = username
                state = 'await_server'


def main() -> None:
    args: Namespace = parse_arguments()
    port: int = args.port
    host: str = args.address

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.connect((host, port))

    # buffer[0] = raw bytes for recv_line
    # buffer[1:] = stdin lines stashed during login's await_server phase
    buffer = [b""]

    if not login(sock, buffer):
        sock.close()
        return

    # Replay any stdin lines that arrived while waiting for the login response
    stashed = buffer[1:]
    buffer[:] = [b""]

    for stashed_line in stashed:
        if not handle_user_input(sock, stashed_line):
            sock.close()
            return

    # Main event loop
    while True:
        readable, _, _ = select.select([sock, sys.stdin], [], [])

        for fd in readable:

            if fd is sock:
                line = recv_line(sock, buffer)

                if line is None:
                    print("Disconnected from server.")
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
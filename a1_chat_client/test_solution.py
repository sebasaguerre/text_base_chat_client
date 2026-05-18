from argparse import Namespace, ArgumentParser
import socket
import select
import sys

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
    buffer[0] is bytes. Reads from sock until a newline is found,
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
        print(f"There are {len(users)} online users:", flush=True)
        for user in users:
            print(user, flush=True)

    elif line == "BAD-RQST-HDR":
        print("Error: Unknown issue in previous message header.", flush=True)

    elif line == "BAD-RQST-BODY":
        print("Error: Unknown issue in previous message body.", flush=True)


def handle_user_input(sock, line):
    """Parse a line of user input. Returns False if the client should quit."""
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
    Handle login using select() on both sock and stdin simultaneously.
    The first prompt is already printed by main() before this is called.

    pending_username tracks the last username we sent HELLO-FROM for:
      - None  → haven't sent anything yet, waiting for user to type
      - "foo" → sent HELLO-FROM foo, waiting for the server to reply

    Returns True on successful login, False on exit/error.
    """
    pending_username = None

    while True:
        readable, _, _ = select.select([sock, sys.stdin], [], [])

        for fd in readable:

            # ── server response ──────────────────────────────────────────
            if fd is sock:
                response = recv_line(sock, buffer)

                if response is None:
                    return False

                # Ignore server messages if we haven't sent anything yet
                if pending_username is None:
                    continue

                if response == f"HELLO {pending_username}":
                    print(f"Successfully logged in as {pending_username}!", flush=True)
                    return True

                elif response == "IN-USE":
                    print(f"Cannot log in as {pending_username}. That username is already in use.", flush=True)
                    pending_username = None
                    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)

                elif response == "BUSY":
                    print("Cannot log in. The server is full!", flush=True)
                    return False

                else:
                    # BAD-RQST-HDR, BAD-RQST-BODY, or anything unexpected
                    print(f"Cannot log in as {pending_username}. That username contains disallowed characters.", flush=True)
                    pending_username = None
                    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)

            # ── user input ───────────────────────────────────────────────
            elif fd is sys.stdin:
                raw = sys.stdin.readline()

                if not raw:
                    return False

                username = raw.strip()

                if username == "!quit":
                    return False

                if contains_forbidden_chars(username):
                    print(f"Cannot log in as {username}. That username contains disallowed characters.", flush=True)
                    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)
                    continue

                # Send HELLO-FROM and record the username we used.
                # If we were already waiting for a server reply, sending a
                # new HELLO-FROM overwrites pending_username — the server
                # will reply to the latest attempt.
                send_msg(sock, f"HELLO-FROM {username}")
                pending_username = username


def main() -> None:
    args: Namespace = parse_arguments()
    port: int = args.port
    host: str = args.address

    # Print the prompt BEFORE connect() so the test sees it immediately,
    # even if connect() fails or blocks because there is no server.
    print("Welcome to Chat Client. Enter your login: ", end="", flush=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.connect((host, port))
    except OSError:
        # No server available — exit cleanly after having printed the prompt
        sock.close()
        return

    buffer = [b""]

    if not login(sock, buffer):
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
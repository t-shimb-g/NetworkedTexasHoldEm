import socket
import json

def render_ui(state):
    """Takes in game state dictionary, unpacks it, and displays terminal UI"""
    you = state["you"]
    players = state["players"]
    board = state["board"]
    pot = state["pot"]
    current = state["current_player"]
    actions = state["available_actions"]
    phase = state["phase"]
    last_move = state["last_move"]

    # Clear screen (works on Windows, Mac, Linux)
    print("\033[2J\033[H", end="")

    print("=" * 50)
    print(' '*10 + f"TEXAS HOLD'EM — {phase}")
    print("=" * 50)

    # --- BOARD ---
    board_str = board if board else "(no cards yet)"
    print(f"Board: {board_str}")
    print(f"Pot: {pot}")
    # last move by previous in players list
    move_str = last_move + " by " + players[(current-1) % len(players)]['name'] if last_move != '' else ''
    print(f"Last Move: {move_str}")
    print("-" * 50)

    # --- PLAYERS ---
    print("Players:")
    for p in players:
        status = []
        if p["state"] == "OUT":
            status.append("FOLDED")
        if p["id"] == current:
            status.append("← TO ACT")

        status_str = f" ({', '.join(status)})" if status else ""

        print(f"{p['name']}: {p['chips']} chips, bet {p['bet']}{status_str}")

    print("-" * 50)

    # --- YOU ---
    print("Your Hand:")
    print("".join(you["cards"]))
    print(f"Your Chips: {you['chips']}   Your Bet: {you['bet']}")
    print("-" * 50)

    # --- ACTIONS ---
    if you["id"] == current:
        print("Your Available Actions:")
        for a in actions:
            if a == 'RAISE':
                print(f" - {a}")
            print(f" - {a}")
    else:
        print(f"Waiting for {players[current]['name']}...")

    print("=" * 50)

def render_summary(summary):
    """Takes in summary dictionary and displays end-of-hand summary in terminal UI"""
    print("\033[2J\033[H", end="")  # clear screen

    print("=" * 50)
    print("              HAND SUMMARY")
    print("=" * 50)

    # --- BOARD ---
    print(f"Board: {summary['board']}")
    print(f"Total Pot: {summary['pot']}")
    print("-" * 50)

    # --- PLAYER CARDS ---
    print("Players:")
    for p in summary["players"]:
        status = "FOLDED" if p["state"] == "OUT" else "SHOWDOWN"
        print(f"{p['name']} ({status}) — {p['cards']}")

    print("-" * 50)

    # --- WINNERS ---
    if summary["winners"]:
        print("Winner(s):")
        for w in summary["winners"]:
            print(f"{w['name']} wins {w['amount']} chips with {w['rank']}")
    else:
        print("No winners? (Split pot or error)")

    print("=" * 50)

def ready_and_wait():
    """Waits for user input to send READY status to server"""
    input("Press ENTER when ready for next hand")
    s.sendall("READY".encode())
    print("Waiting for other players to ready...")


if __name__ == '__main__':
    HOST = input("Enter IP address of the server: ")
    PORT = input("Enter port of the server: ")
    name = input("Input a player name: ")

    print("Attempting to connect...")
    s = socket.socket()
    s.connect((HOST, PORT))
    s.sendall(name.encode())
    print("Connected!")

    # wait for server to fill or timeout to finish
    print("Waiting for server...")
    ready_and_wait()

    while True:
        data = s.recv(4096).decode()
        if not data:
            print("Disconnected from server")
            break

        game_state = json.loads(data)

        if game_state["hand_ended"]:
            render_summary(game_state["summary"])
            ready_and_wait()
            continue

        render_ui(game_state)
        if game_state["you"]["id"] == game_state["current_player"]:
            action = input("> ")
            s.sendall(action.encode())
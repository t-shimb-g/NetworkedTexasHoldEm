from texasholdem.game.game import TexasHoldEm
from texasholdem.card.card import card_list_to_pretty_str
from texasholdem.game.action_type import ActionType
from texasholdem.evaluator import evaluator
from texasholdem.game import history
import socket
import json
import time

def get_player_game_state(game, players, player_id, ended=False):
    """Packages a JSON containing player specific game data"""
    game_state = {
        "you" : {
            "id" : player_id,
            "name" : players[player_id][1],
            "cards" : card_list_to_pretty_str(game.get_hand(player_id)),
            "chips" : game.players[player_id].chips,
            "bet" : game.player_bet_amount(player_id)
        },
        "players" : [], # filled below
        "board" : card_list_to_pretty_str(game.board),
        "pot" : game.pots[0].get_total_amount(), # includes bets of current round in pot total
        "current_player" : game.current_player,
        "available_actions" : [], # filled below
        "phase" : game.hand_phase.name,
        "last_move" : (), # filled below
        "game_state" : game.game_state.name,
        "hand_ended" : ended,
    }

    for player in game.players:
        game_state["players"].append({
            "id" : player.player_id,
            "name" : players[player.player_id][1],
            "chips" : player.chips,
            "state" : player.state.name,
            "bet" : game.player_bet_amount(player.player_id)
        })

    moves = game.get_available_moves()
    for action in moves.action_types:
        if action == ActionType.RAISE:
            r = moves.raise_range
            game_state["available_actions"].append(f"RAISE {r.start}-{r.stop - 1}")
        else:
            game_state["available_actions"].append(action.name)

    last_move = game.action
    last_move_str = last_move[0].name if last_move[0] else ''
    last_move_str += ' ' + str(last_move[1]) if last_move[1] else ''
    game_state["last_move"] = last_move_str

    if ended:
        game_state["summary"] = hand_summary(game, players)

    return json.dumps(game_state)

def send_game_states(game, players):
    """Sends respective JSON data to each player"""
    for player_id, (player_conn, _) in players.items():
        player_game_state = get_player_game_state(game, players, player_id)
        player_conn.sendall(player_game_state.encode())

def interpret_action(game, action_str):
    """Both validates a move and also takes the move if valid"""
    action_str = action_str.strip().upper()
    parts = action_str.split() # if only 1 word, it just gets put into a list

    action = None
    raise_amount = None

    try:
        if parts[0] == 'RAISE':
            action = ActionType.RAISE
            raise_amount = int(parts[1])
        elif parts[0] == 'ALL_IN': action = ActionType.ALL_IN
        elif parts[0] == 'CALL': action = ActionType.CALL
        elif parts[0] == 'CHECK': action = ActionType.CHECK
        elif parts[0] == 'FOLD': action = ActionType.FOLD
        else: raise ValueError

        if not game.validate_move(action=action, total=raise_amount):
            raise ValueError
        game.take_action(action, total=raise_amount)
        return True

    except ValueError:
        print(f"Invalid move: {parts}")
        return False

def wait_for_ready(players):
    """Waits to receive a READY msg from all players"""
    ready = [False for _ in players]

    while False in ready:
        for id, (conn, _) in players.items():
            if not ready[id]:
                msg = conn.recv(4096).decode()
                if msg == "READY":
                    ready[id] = True

def wait_for_connections(server, max_players=9, timeout=30):
    """
    Returns dictionary of socket connections and player names:
    {id: (player_connection, player_name)}
    """
    print(f"Waiting for up to {MAX_PLAYERS} connections...")
    players = {}
    start_time = time.time()

    # loop while still player count < max or have not timed out
    while len(players) < max_players and time.time() - start_time < timeout:
        server.settimeout(1)
        try:
            player_conn, _ = server.accept()
            player_name = player_conn.recv(4096).decode().strip()
            player_id = len(players)
            players[player_id] = (player_conn, player_name)
            print(f"{player_name} connected ({len(players.keys())}/{MAX_PLAYERS})")
        except TimeoutError: # raised by server socket every second in order to check timer
            pass

    return players

def get_action(game, players):
    """Receives plaintext action from player"""
    current_conn, current_name = players[game.current_player]
    print(f"{current_name}'s move...")
    return current_conn.recv(4096).decode()

def handle_disconnect(game, players):
    """Forces FOLD action, closes connection to player, removes from player list"""
    conn, name = players[game.current_player]
    print(f"{name} has disconnected, folding...")
    game.take_action(ActionType.FOLD)
    conn.close()
    players.pop(game.current_player)

def has_winner(game):
    """
    Checks how many players have chips.
    If there is more than 1 player with chips, play can continue
    """
    has_chips = 0
    for p in game.players:
        if p.chips > 0:
            has_chips += 1
    return has_chips == 1

def hand_summary(game, players):
    """Constructs dictionary containing end-of-hand information"""
    summary = {
        "board": card_list_to_pretty_str(game.board),
        "pot": game.pots[0].get_total_amount(),
        "players": [],
        "winners": []
    }

    # Show each player's final hand
    for p in game.players:
        summary["players"].append({
            "id": p.player_id,
            "name": players[p.player_id][1],
            "cards": card_list_to_pretty_str(game.get_hand(p.player_id)),
            "rank": evaluator.rank_to_string(evaluator.evaluate(game.board, game.get_hand(p.player_id))),
            "state": p.state.name
        })

    # pot_winners = { pot_id: (amount, best hand, list of winners) }
    winners = game.hand_history.settle.pot_winners.values()

    for amount, best_rank, winner_list in winners:
        summary["winners"].append({
            "id": winner_list[0],
            "name": players[winner_list[0]][1],
            "rank": evaluator.rank_to_string(best_rank),
            "amount": amount
        })

    return summary

def send_summary(game, players):
    """Same as send_game_states except enables sending hand summary as well"""
    print("Hand ended")
    for player_id, (player_conn, _) in players.items():
        player_game_state = get_player_game_state(game, players, player_id, ended=True)
        player_conn.sendall(player_game_state.encode())

def run_game(game, players):
    """Main game loop"""
    print("Starting hand!")
    game.start_hand()
    while game.is_hand_running():
        send_game_states(game, players) # send out the game state to each player
        current_action = get_action(game, players)
        if not current_action: # player disconnected
            handle_disconnect(game, players)
            continue

        if not interpret_action(game, current_action):
            continue # invalid move, prompts for new action


if __name__ == '__main__':
    IP, PORT = '0.0.0.0', 8080
    MAX_PLAYERS = 9

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((IP, PORT))
    s.listen(MAX_PLAYERS)

    print("Server running on", (IP, PORT))

    TIMEOUT = 30

    # {id: (player_connection, player_name)}
    players = wait_for_connections(s, MAX_PLAYERS, TIMEOUT)
    while len(players) < 2:
        print("Need at least 2 players. Reopening game")
        players = wait_for_connections(s, MAX_PLAYERS, TIMEOUT)
    print("Entering lobby...")

    game = TexasHoldEm(buyin=500, big_blind=50, small_blind=25, max_players=len(players))

    while True:
        wait_for_ready(players) # wait here until all players send ready message
        run_game(game, players)
        send_summary(game, players)
        if has_winner(game):
            print("Thanks for playing!")
            for conn, _ in players.values():
                conn.close()
            break
# Networked Texas Hold'em Poker
This is a network extension of the [`TexasHoldEm`](https://github.com/SirRender00/texasholdem/tree/v0.11.0/) python library. It features
all of the same gameplay, except the players are all on separate machines!
The game is ran on a server machine which manages the entire game loop.
- Full Texas Hold'em gameplay
- Client-server architecture
- Lightweight socket protocol

## Server Setup
1. Python 3.11 or later is required. Install [here](https://www.python.org/downloads/).
2. In root project directory, run `python -m venv .venv` to create Python virtual environment
3. Run the following command to activate the environment:
   - Windows (Command Prompt): `.venv\Scripts\activate`
   - Windows (PowerShell): `.venv\Scripts\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`
4. Install `TexasHoldEm` using `pip install texasholdem`

## Using
- `server.py` is the only script that requires [`TexasHoldEm`](https://github.com/SirRender00/texasholdem/tree/v0.11.0/). It accepts all traffic trying to connect.
- `client.py` simply needs to be ran and the follow the prompts.
- Run `server.py` first, connect using `client.py` on different machines, and play poker!

## Code Examples
### Server loop
Below is how the server opens for connections, creates the game,
and begins the main game loop.
```python
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
```

### Player specific game states
This function creates the player specific (meaning it has information only pertaining to that player)
`game_state` dictionary.
In this function is where the game object gets interacted with the most.
It constructs the dictionary that gets sent to the client and unpacked and rendered
in the terminal.
```python
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
```

### Client loop
The client loop is as simple as constantly receiving data from the server,
and only sending data if the server says so via `game_state["current_player"]`.
Each time the client receives, it always renders the data for the user to see
in the terminal.
```python
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
```
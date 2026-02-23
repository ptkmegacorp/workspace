import json

BOARD_ROWS = 6
BOARD_COLS = 7
STATE_FILE = "/home/bot/.openclaw/workspace/projects/connect4_state.json"

def init_game():
    state = {
        "board": [[None for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)],
        "current_player": "red",  # red goes first
        "game_over": False,
        "winner": None
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
    return state

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return init_game()

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def drop_piece(col):
    state = load_state()
    if state["game_over"]:
        return state
    
    col = col - 1  # Convert 1-7 to 0-6
    if col < 0 or col >= BOARD_COLS:
        return state
    
    # Find lowest empty row
    for row in range(BOARD_ROWS - 1, -1, -1):
        if state["board"][row][col] is None:
            state["board"][row][col] = state["current_player"]
            
            # Check win
            if check_win(state["board"], row, col):
                state["game_over"] = True
                state["winner"] = state["current_player"]
            else:
                # Switch player
                state["current_player"] = "red" if state["current_player"] == "yellow" else "yellow"
            break
    
    save_state(state)
    return state

def check_win(board, row, col):
    player = board[row][col]
    
    # Check all directions
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    
    for dr, dc in directions:
        count = 1
        
        # Check positive direction
        r, c = row + dr, col + dc
        while 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS and board[r][c] == player:
            count += 1
            r += dr
            c += dc
        
        # Check negative direction
        r, c = row - dr, col - dc
        while 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS and board[r][c] == player:
            count += 1
            r -= dr
            c -= dc
        
        if count >= 4:
            return True
    
    return False

def render_board(state):
    board = state["board"]
    lines = ["Connect 4 🕹️", ""]
    
    # Column numbers
    lines.append("  1   2   3   4   5   6   7")
    lines.append("+" + "---+" * 7)
    
    for row in range(BOARD_ROWS):
        line = "|"
        for col in range(BOARD_COLS):
            cell = board[row][col]
            if cell == "red":
                line += " 🔴 |"
            elif cell == "yellow":
                line += " 🟡 |"
            else:
                line += "   |"
        lines.append(line)
        lines.append("+" + "---+" * 7)
    
    if state["game_over"]:
        winner_emoji = "🔴" if state["winner"] == "red" else "🟡"
        lines.append(f"\n{winner_emoji} WINS! 🎉")
        lines.append("Game over! Start a new game.")
    else:
        turn_emoji = "🔴" if state["current_player"] == "red" else "🟡"
        lines.append(f"\n{turn_emoji} Your turn!")
    
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            init_game()
            print("Game initialized!")
        elif sys.argv[1] == "drop" and len(sys.argv) > 2:
            col = int(sys.argv[2])
            state = drop_piece(col)
            print(render_board(state))
        elif sys.argv[1] == "show":
            state = load_state()
            print(render_board(state))

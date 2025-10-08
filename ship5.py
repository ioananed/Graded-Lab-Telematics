
# Design of Telematics Systems 2025-26
# Universidad Carlos III de Madrid
#
# Ship controlled by captain or moving randomly.
# Step 2: adds signal handling (SIGALRM, SIGUSR1, SIGUSR2, SIGQUIT, SIGTSTP)
# Step 4: adds communication with the captain using a PIPE (Inter-Process Communication)
#
# Parameters:
#   --id <shipId>        Ship ID given by the captain
#   --map <file>         Path to map file (default: map.txt)
#   --pos x y            Initial position
#   --food N             Initial food (default: 100)
#   --random N s1        Random movement: N steps, s1 seconds between moves
#   --captain            Follow captain’s orders (not implemented yet in Step 2)
#   --pipe <fd>          File descriptor (write end) of the pipe to send messages to the captain
#
# All output is sent to stderr (to show logs on the terminal)
# Messages to the captain (real-time updates) go through the pipe
        

import os
import sys
import time
import signal
import random
import argparse
from map import Map

ursula_pipe = None

# SHIP CLASS

class Ship:
    # DIRECTIONS: Possible moves → right, down, left, up
    DIRECTIONS = [(0, 1), (1, 0), (0, -1), (-1, 0)]

    def __init__(self, shipId, mapa, pos, food, pipe_fd=None):
        # Stores all the attributes of the ship
        self.shipId = shipId           # Ship unique ID (provided by captain)
        self.mapa = mapa               # Map object (shared map between ships)
        self.pos = pos                 # Current (x, y) position on the map
        self.mapa.set_ship(self.pos[0], self.pos[1])  # Mark position on map
        self.food = food               # Food supply (decreases every move)
        self.gold = 0                  # Gold collected by visiting islands
        self.pipe_fd = pipe_fd         # File descriptor of pipe to captain (write end)
        self.pid = os.getpid()         # Process ID of this ship
        self.speed = 0                 # Movement interval in seconds (used by SIGALRM)

 
    # Function to send a message both to stderr and to the captain via pipe
    def speak(self, msg: str):
        """
        Send short status messages ('OK', 'NOK', 'exit') to the captain via stdout,
        and everything else to stderr for local debugging.
        """
        if msg in ["OK", "NOK", "exit"]:
            print(msg, flush=True)  # this goes to the captain
        else:
            print(msg, file=sys.stderr, flush=True)  # debug output only

 
    # Default string representation of the ship (used in debugging)
  
    def __str__(self):
        return f"Ship {self.shipId} (PID {self.pid}) at {self.pos} with {self.food} food and {self.gold} gold."

    # Returns a formatted message with current ship status (for SIGTSTP)

    def get_status_message(self):
        return f"Ship {self.shipId} (PID {self.pid}) → Position: {self.pos}, Food: {self.food}, Gold: {self.gold}"

  
    # RANDOM MOVEMENT:
    #   - Ship consumes 5 food per movement
    #   - If enough food, picks a random direction and tries to move
    #   - If lands on BAR → gains 10 gold
    #   - If lands on HOME → gains 20 food
    #   - If blocked → message shown
 
    def move_randomly(self):
        if self.food < 5:
            self.speak(f"Ship {self.shipId}: Not enough food to move.")
            return
        # Pick a random direction (dx, dy)
        dx, dy = random.choice(Ship.DIRECTIONS)
        # Check if the destination cell is navigable
        if self.mapa.can_sail(self.pos[0] + dx, self.pos[1] + dy):
            self.mapa.remove_ship(self.pos[0], self.pos[1])  # Remove from old cell
            self.pos = (self.pos[0] + dx, self.pos[1] + dy)  # Update position
            self.mapa.set_ship(self.pos[0], self.pos[1])      # Mark on new cell
            self.food -= 5  # Food cost per move

            # Determine the type of terrain we landed on
            where = self.mapa.get_cell_type(self.pos[0], self.pos[1])
            if where == Map.BAR:
                self.gold += 10
                self.speak(f"Ship {self.shipId}: Found island {self.pos}, gold={self.gold}")
            elif where == Map.HOME:
                self.food += 20
                self.speak(f"Ship {self.shipId}: Reached port {self.pos}, food={self.food}")
            else:
                self.speak(f"Ship {self.shipId}: Moved to {self.pos}, food={self.food}")
        else:
            self.speak(f"Ship {self.shipId}: Cannot sail there.")
        # Delay for realism
        time.sleep(1)

   
    # CAPTAIN MODE: waits for commands from captain via stdin (Step 3)
   
    def move_captain(self):
        global ursula_pipe
        #self.speak(f"Ship {self.shipId} (PID {self.pid}) in Captain Mode")
        while True:
            try:
                movement = sys.stdin.readline().strip()
                if not movement:
                    continue  # sigue esperando si no hay comando

                if movement == "exit":
                    self.speak("exit")
                    print(f"Ship {self.shipId} exiting with gold {self.gold}.", file=sys.stderr)
                    sys.exit(self.gold)

                if self.food < 5:
                    self.speak("NOK")
                    print(f"Ship {self.shipId}: Not enough food.", file=sys.stderr)
                    continue

                # current position
                x, y = self.pos
                new_x, new_y = x, y
                if movement == "up": new_y += 1
                elif movement == "down": new_y -= 1
                elif movement == "right": new_x += 1
                elif movement == "left": new_x -= 1

                # check destination
                if self.mapa.can_sail(new_x, new_y):
                    self.mapa.remove_ship(x, y)
                    self.pos = (new_x, new_y)
                    self.mapa.set_ship(new_x, new_y)
                    self.food -= 5
                    self.speak("OK")
                    #print(f"Ship {self.shipId} moved to {self.pos}", file=sys.stderr)
                    if ursula_pipe:
                        try:
                            move_msg = f"{self.pid},MOVE,{self.pos[0]},{self.pos[1]},{self.food},{self.gold}"
                            send_to_ursula(move_msg, ursula_pipe)
                        except OSError as e:
                            print(f"Ship {self.shipId}: Error sending MOVE to Ursula: {e}", file=sys.stderr)
                    
                else:
                    self.speak("NOK")
                    print(f"Ship {self.shipId}: Cannot sail there", file=sys.stderr)

            except Exception as e:
                self.speak(f"Error happened: {e}")
                print(f"Ship {self.shipId} exception: {e}", file=sys.stderr)


def send_to_ursula(message, ursula_pipe):
    try:
        if not ursula_pipe:
            return
        with open(ursula_pipe, "w") as fifo:
            fifo.write(message + "\n")
            fifo.flush()
    except OSError as e:
        print(f"Error happened: {e}", file=sys.stderr)
        
# SIGNAL HANDLERS

# They manage how the ship reacts to external signals sent by the captain

def handler_sigalrm(signum, frame):
    global current_ship
    current_ship.move_randomly()
    os.alarm(current_ship.speed)  # Set next timer

def handler_sigusr1(signum, frame):
   
    global current_ship
    current_ship.food += 10
    current_ship.speak(f"Ship {current_ship.shipId}: Food increased → {current_ship.food}")

def handler_sigusr2(signum, frame):
   
    global current_ship
    current_ship.food = max(0, current_ship.food - 10)
    current_ship.gold = max(0, current_ship.gold - 10)
    current_ship.speak(f"Ship {current_ship.shipId}: Food/Gold decreased → {current_ship.food}/{current_ship.gold}")
    if current_ship.food == 0:
        current_ship.speak(f"Ship {current_ship.shipId}: Out of food → exiting ({current_ship.gold})")
        sys.exit(current_ship.gold)

def handler_sigquit(signum, frame):
    
    global current_ship
    current_ship.speak(f"Ship {current_ship.shipId}: Received SIGQUIT → exit ({current_ship.gold})")
    sys.exit(current_ship.gold)

def handler_sigtstp(signum, frame):
   
    global current_ship
    current_ship.speak(current_ship.get_status_message())



# MAIN FUNCTION

if __name__ == "__main__":
    # Argument parser: reads command-line parameters sent by the captain
    ap = argparse.ArgumentParser(description="Pirate Ship (Step 4)")
    ap.add_argument("--id", type=int, required=True, help="Ship ID assigned by captain")
    ap.add_argument("--map", type=str, default="map.txt", help="Map file path")
    ap.add_argument("--pos", type=int, nargs=2, metavar=("x", "y"), default=(0, 0), help="Initial position")
    ap.add_argument("--food", type=int, default=100, help="Initial food amount")
    ap.add_argument("--random", type=int, nargs=2, metavar=("N", "s1"), help="Random mode (N steps, s1 seconds)")
    ap.add_argument("--captain", action="store_true", help="Captain controls the ship")
    ap.add_argument("--pipe", type=int, help="Pipe file descriptor from captain (for IPC)")
    ap.add_argument("--ursula", type=str, help="Pipe for ursula.py,ursula_pipe")

    args = ap.parse_args()
    
    ursula_pipe = args.ursula

    # Prevent invalid combination of captain and random mode
    if args.captain and args.random:
        sys.exit("Cannot use --captain and --random together.")

    # Load map and validate starting position
    mapa = Map(args.map)
    if not mapa.can_sail(args.pos[0], args.pos[1]):
        sys.exit("Invalid initial position.")

    # Create the ship object
    ship = Ship(args.id, mapa, args.pos, args.food, args.pipe)
    global current_ship
    current_ship = ship
    if args.random:
        ship.speed = args.random[1]

    # Starting message
    print(f"Ship {ship.shipId} started with PID {ship.pid}", file=sys.stderr, flush=True)
    if ursula_pipe:
            init_msg = f"{ship.pid},INIT,{ship.pos[0]},{ship.pos[1]},{ship.food},{ship.gold}"
            print(f"mensaje de {ship.pid} :{init_msg}")
            try:
                with open(ursula_pipe, "w") as fifo:
                    fifo.write(init_msg + "\n")
                    fifo.flush()
                    print("enviado ship")
            except OSError as e:
                print(f"Error happened: {e}", file=sys.stderr)

   
    # INSTALLATION OF SIGNAL HANDLERS
    
    signal.signal(signal.SIGALRM, handler_sigalrm)  # For periodic movement
    signal.signal(signal.SIGUSR1, handler_sigusr1)  # Add food
    signal.signal(signal.SIGUSR2, handler_sigusr2)  # Subtract food/gold
    signal.signal(signal.SIGQUIT, handler_sigquit)  # Quit ship
    signal.signal(signal.SIGTSTP, handler_sigtstp)  # Print ship status

  
    # BEHAVIOR DEPENDING ON MODE
    
    if args.captain:
        # Step 3: Captain sends commands manually
        ship.move_captain()
    elif args.random:
        # Step 4: Automatic mode – move periodically by SIGALRM
        os.alarm(ship.speed)  # Start periodic timer
        while True:
            try:
                # Wait for signals (SIGALRM, SIGQUIT, etc.)
                signal.pause()
            except SystemExit:
                break  # When the ship exits normally

    # Ship terminates and returns gold as exit code
    ship.speak(f"Ship {ship.shipId} (PID {ship.pid}) finished with {ship.gold} gold.")
    sys.exit(ship.gold)
    
    if ursula_pipe:
        try:
            term_msg = f"{ship.pid},TERMINATE\n"
            with open(ursula_pipe, "w") as fifo:
                fifo.write(term_msg)
                fifo.flush()
        except OSError as e:
            print(f"Error happened: {e}", file=sys.stderr)
           
    sys.exit(ship.gold)

 
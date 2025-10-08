import os
import sys
import random
import signal

class Ursula:
    def __init__(self, ursula_pipe):
        self.ursula_pipe = ursula_pipe
        self.treasure = 100
        self.captains = {} 
        self.ships = {}    
        self.running = True
        
    def create_named_pipe(self):
        #si no existe el named pipe, fifo, lo crea
        try:
            if not os.path.exists(self.ursula_pipe):
                os.mkfifo(self.ursula_pipe)
                print(f"Created named pipe '{self.ursula_pipe}'", file=sys.stderr)
            else:
                print(f"Named pipe '{self.ursula_pipe}' already exists", file=sys.stderr)
        except OSError as e:
            print(f"Error happened: {e}", file=sys.stderr)
            sys.exit(1)
    
    def handle_fight(self, ship_pid, x, y):
        #handle fights between ships, when two ships are in the same position
        ships_in_cell = []
        for pid, ship_data in self.ships.items():
            if pid != ship_pid and ship_data['x'] == x and ship_data['y'] == y:
                ships_in_cell.append(pid)
        
        if not ships_in_cell:
            return  #no fight, only one ship in the cell
        
        # Include the ship that just moved
        all_ships_in_fight = ships_in_cell + [ship_pid]
        print(f"Fight detected at ({x},{y}) between ships: {all_ships_in_fight}", file=sys.stderr)
        # Randomly select a winner
        winner_pid = random.choice(all_ships_in_fight)
        losers = [pid for pid in all_ships_in_fight if pid != winner_pid]
        
        print(f"Ursula: Winner is ship {winner_pid}", file=sys.stderr)
        # Winner gets 10 gold
        self.ships[winner_pid]['gold'] += 10
        print(f"Ursula: Ship {winner_pid} gains 10 gold (now: {self.ships[winner_pid]['gold']})", file=sys.stderr)
        
        # Handle losers
        total_gold_needed = 0
        for loser_pid in losers:
            # Losers lose 10 food and 10 gold
            self.ships[loser_pid]['food'] = max(0, self.ships[loser_pid]['food'] - 10)
            gold_lost = min(10, self.ships[loser_pid]['gold'])
            self.ships[loser_pid]['gold'] -= gold_lost
            total_gold_needed += (10 - gold_lost) #compensación que tiene que poner Ursula si no tiene uno suficiente gold
            
            print(f"Ursula: Ship {loser_pid} loses 10 food (now: {self.ships[loser_pid]['food']}) and {gold_lost} gold (now: {self.ships[loser_pid]['gold']})", file=sys.stderr)
        
        # Handle gold
        if total_gold_needed > 0:
            if self.treasure >= total_gold_needed:
                self.treasure -= total_gold_needed
                print(f"Ursula: Paid {total_gold_needed} gold from treasure (remaining: {self.treasure})", file=sys.stderr)
            else:       
                # End of the world 
                print(f"Ursula: Not enough gold. Only {self.treasure} available, need {total_gold_needed}", file=sys.stderr)
                self.end_of_world()
       
    def end_of_world(self):
        #ends all captains for the end of the world
        print("Ursula: end of the world, no enough food", file=sys.stderr)
        for captain_pid in self.captains.keys():
            try:
                os.kill(captain_pid, signal.SIGUSR1)  
                print(f"Ursula: Sent emergency signal to captain {captain_pid}", file=sys.stderr)
            except OSError as e:
                print(f"Error happened: {e}", file=sys.stderr)
        
        self.running = False
    
    def process_message(self, message):
        #procesa los mensajes del captain
        try:
            parts = message.strip().split(',')
            pid = int(parts[0])
            msg_type = parts[1]
            
            if msg_type == "INIT_CAPT":
                # Captain initialization
                self.captains[pid] = "alive"
                print(f"Ursula: Captain {pid} registered", file=sys.stderr)
                
            elif msg_type == "END_CAPT":
                # Captain termination
                if pid in self.captains:
                    self.captains[pid] = "terminated"
                    print(f"Ursula: Captain {pid} terminated", file=sys.stderr)
                
            elif msg_type == "INIT":
                # Ship initialization
                x, y, food, gold = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                self.ships[pid] = {
                    'x': x, 
                    'y': y, 
                    'food': food, 
                    'gold': gold,
                    'captain_pid': None
                }
                print(f"Ursula: Ship {pid} initialized at ({x},{y}) with food={food}, gold={gold}", file=sys.stderr)
                
            elif msg_type == "MOVE":
                # Ship movement
                x, y, food, gold = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                if pid in self.ships:
                    self.ships[pid].update({
                        'x': x, 
                        'y': y, 
                        'food': food, 
                        'gold': gold
                    })
                    print(f"Ursula: Ship {pid} moved to ({x},{y}) with food={food}, gold={gold}", file=sys.stderr)
                    
                    # Check for fights
                    self.handle_fight(pid, x, y)
                    
                    # Print status of all ships
                    self.print_ship_status()
                
            elif msg_type == "TERMINATE":
                # Ship termination
                if pid in self.ships:
                    del self.ships[pid]
                    print(f"Ursula: Ship {pid} terminated", file=sys.stderr)
            
            # Check if all captains and ships have terminated
            self.check_termination()
            
        except OSError as e:
            print(f"Error processing: {e}", file=sys.stderr)
    
    def print_ship_status(self):
        #printea el status de los ships
        print("\n--- URSULA'S SHIP STATUS ---", file=sys.stderr)
        print(f"Treasure: {self.treasure} gold", file=sys.stderr)
        for pid, ship_data in self.ships.items():
            print(f"Ship {pid}: pos=({ship_data['x']},{ship_data['y']}), food={ship_data['food']}, gold={ship_data['gold']}", file=sys.stderr)
        print("--- END STATUS ---\n", file=sys.stderr)
        sys.stderr.flush()
    
    def check_termination(self):
        #check if all the captains have been ended
        if not self.captains:
            return
            
        all_captains_terminated = all(status == "terminated" for status in self.captains.values())
        no_ships_remaining = len(self.ships) == 0
        
        if all_captains_terminated and no_ships_remaining:
            print("Ursula: All captains and ships have terminated.", file=sys.stderr)
            self.running = False
    
    # def run(self):
    #     #to read the named pipe
    #     self.create_named_pipe()
        
    #     print(f"Ursula: Waiting for messages on '{self.ursula_pipe}'...", file=sys.stderr)
    #     print(f"Ursula: Initial gold: {self.treasure} ", file=sys.stderr)
                 
    #     try:
    #         pipe=open(self.ursula_pipe, 'r')
    #         while (self.running):
    #             print("open pipe", file=sys.stderr)
    #             message = pipe.readline()
                
    #             if not message:
    #                 continue
    #             print(f"mensaje recibido:{message}")
    #             if message:
    #                 self.process_message(message)
    #         pipe.close(pipe)
    #         print("Ursula: Shutting down.", file=sys.stderr)
    #     except OSError as e:
    #         print(f"Error happened: {e}", file=sys.stderr)
    #         try:
    #             if os.path.exists(self.ursula_pipe):
    #                 os.unlink(self.ursula_pipe)
    #                 print(f"Ursula: Removed named pipe '{self.ursula_pipe}'", file=sys.stderr)
    #         except OSError as e:
    #             print(f"Error happened: {e}", file=sys.stderr)
    def run(self):
        self.create_named_pipe()
        print(f"Ursula: Waiting for messages on '{self.ursula_pipe}'...", file=sys.stderr)
        print(f"Ursula: Initial gold: {self.treasure}", file=sys.stderr)

        while self.running:
            try:
                # Blocks here until some writer opens the FIFO
                with open(self.ursula_pipe, "r") as pipe:
                    for line in pipe:              # reads until EOF (all writers closed)
                        line = line.strip()
                        if not line:
                            continue
                        # print(f"Ursula: received: {line}", file=sys.stderr)  # optional debug
                        self.process_message(line)
                # Reaching here means EOF (all writers closed). Loop will reopen and block again.
            except OSError as e:
                print(f"Error happened: {e}", file=sys.stderr)

        # Optional cleanup when self.running becomes False
        try:
            if os.path.exists(self.ursula_pipe):
                os.unlink(self.ursula_pipe)
                print(f"Ursula: Removed named pipe '{self.ursula_pipe}'", file=sys.stderr)
        except OSError as e:
            print(f"Error happened: {e}", file=sys.stderr)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 ursula.py <ursula_pipe>", file=sys.stderr)
        sys.exit(1)
    
    ursula_pipe = sys.argv[1]
    ursula = Ursula(ursula_pipe)
    ursula.run()

if __name__ == "__main__":
    main()
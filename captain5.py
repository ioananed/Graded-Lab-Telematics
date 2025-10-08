import map
import os
import argparse, sys, signal
from map import Map   #lo añadí pq si no no te deja entrar a argumento map

ship_dict = {}    #dictionary del capitan to control los ships
mapa = None
ursula_pipe = None
all_finished = False
       
#Para pasar los argumentos creamos una primera función llamada pasarArgumentos 
def arguments():
    ap = argparse.ArgumentParser(description='Captain creating fleet of ships')
    ap.add_argument("--name", type=str, default="Captain Amina al-Sirafi", help="Name of the captain")
    ap.add_argument("--map", type=str, default="map.txt", help="map file path")
    ap.add_argument("--ships", type=str, default="ships.txt", help="ship info file path")
    ap.add_argument("--random", action= "store_true", default=0, help="if flag given, move randomly") # action only to use the captain command when it's present and if not, random movement
    ap.add_argument("--ursula", type=str, help="Pipe for ursula.py, ursula_pipe")
    return ap.parse_args()  #returns arguments 

def send_to_ursula(message, ursula_pipe):
    if ursula_pipe:
        try:
            with open(ursula_pipe, "w") as fifo:
                fifo.write(message + "\n")
                #fifo.flush()
            print(f"Captain: sent message to Ursula: {message}", file=sys.stderr)
        except OSError as e:
            print(f"Error happened: {e}", file=sys.stderr)

def read_ship_info(file_path):
#argumentos:
    ship = []     #para guardar datos de ship.txt
    try: 
        with open(file_path, 'r') as fileShips:
            for line in fileShips:  #for each line on the file
                if not line.strip(): #Removes whitespaces and reads what isn't a whitespace
                    continue
                parts = line.split() #we are dividing the line in three parts we are going to store in the list: id, position, speed.
                              
                if len(parts) < 3: #makes sure there is an ID, pos and speed
                    continue
                
                #poner int(parts[0])
                #For ID
                shipId = parts[0]
                #For the position:
                position = parts[1].strip("()").split(",") #this is an array that stores the positions so we can later separate them into two directions
                x = position[0]
                y = position[1]
                #For the speed:
                speed = parts[2]
                ship.append((shipId, x, y, speed))

                print(f"Ship ID: {shipId}, Pos: ({x},{y}), Speed: {speed}", file=sys.stderr)
                sys.stderr.flush()
            return ship
    except OSError as e:
        print(f"Error happened: {e}", file=sys.stderr)
        sys.stderr.flush()
        sys.exit(1)


#SIGNALS
def handler_sigint(signo, frame):
    global ursula_pipe
    signame = signal.strsignal(signo)
    sigpid = os.getpid()
    print(f'[{sigpid}] Caught signal {signame} ({signo})')
    sys.stderr.flush()
    print("Captain will finish. Sending SIGQUIT to all ships...")
    sys.stderr.flush()

    #send SIGQUIT to ships (kill them)
    for ship in ship_dict.values():
        try: 
            os.kill(ship["pid"], signal.SIGQUIT)
        except OSError as e:
         print(f"Error happened: {e}", file=sys.stderr)
         sys.stderr.flush()

    #wait until ships are terminated
    for ship in list(ship_dict.values()):
        try:
            pid_fin, status = os.waitpid(ship["pid"], 0)   #waits for each ship. not use os.wait() bc it may show the ship in the wrong order
            if os.WIFEXITED(status):
                code = os.WEXITSTATUS(status)   #exit code
                print(f"Ship {pid_fin} exited with code {code}")
                sys.stderr.flush()
            else:
                print(f"Ship {pid_fin} not terminated as expected")
                sys.stderr.flush()
        except OSError as e:
            print(f"Error happened: {e}", file=sys.stderr)
            sys.stderr.flush()

    if ursula_pipe:
        send_to_ursula(f"{os.getpid()},END_CAPT", ursula_pipe)
        for ship in ship_dict.values():
            try:
                end_msg = f"{os.getpid()},END_CAPT\n"
                os.close(ship["w_pipe"])
                os.close(ship["r_pipe"])
                print("Captain: Sent termination to Ursula", file=sys.stderr)
            except OSError as e:
                print(f"Error sending termination to Ursula: {e}", file=sys.stderr)

    print("All ships finished. Captain exits.")
    sys.stderr.flush()
    sys.exit(0)   #0 for all exited correctly, 1 when exited with problems


def handler_sigchld(signo, frame):      #ESTO SALE DISTINTO
    print("Captain received SIGCHLD", file=sys.stderr)
    sys.stderr.flush()
    signame = signal.strsignal(signo)           #signal name
    sigpid = os.getpid()      
    print(f'[{sigpid}] Caught signal {signame} ({signo})')
    sys.stderr.flush()
    if (signo == signal.SIGCHLD):
        pid_fin, status = os.wait()
    if os.WIFEXITED(status) :
        print(f'Child {pid_fin} exit code: {os.WEXITSTATUS(status)}')
        sys.stderr.flush()
    else:
        print(f'Child {pid_fin} completed')
        sys.stderr.flush()

#PIPES
def send_command(shipId, command):
    global mapa   #to be able to access map
    shipId_dict = ship_dict.get(shipId)     #get each ship Id del dictionary
    if not shipId_dict:     #if ship doesnt exist, return
        print("Invalid ship ID.", file=sys.stderr)
        return

    if command not in ["up", "down", "left", "right", "exit"]:  #if command isnt one of the established, return
        print("Invalid command.", file=sys.stderr)
        return

    #Verificar si puede moverse el barco --> captain. 
    #Mover el barco --> ships
    #Simulate movement to check for collision --> captain has to coordinate all ships. Cannot be only in ships.py bc a ship doesnt know the position of other ships
    # new position of ship
    x, y = shipId_dict["pos"]        #Usas el shipId del diccionario para saber de que ship hablas. x, y son la posicion inicial del ship q coge del dict y luego la actualiza sumando o restando al mover
    new_x , new_y = x, y
    if command == "up": new_y += 1
    elif command == "down": new_y -= 1
    elif command == "right": new_x += 1
    elif command == "left": new_x -= 1
    new_pos = (new_x, new_y)    #esta es la pos final del ship, pero no la actualiza al ship, sino q es para verificar si se puede mover ahí el barco

    print(f"Sending action {command} to ship {shipId}", file=sys.stderr)
    sys.stderr.flush()
    #to avoid collisions
    if command != "exit":
        #HAY QUE CONSEGUIR QUE NO VEA A LOS SHIPS DE OTRAS FLOTAS COMO ROCKS
        if mapa.get_cell_type(new_pos[0], new_pos[1]) == Map.ROCK: #verifica si es una roca u otro barco de otra flota
            print(f"Invalid move: Cell ({new_pos[0]},{new_pos[1]}) is a rock.", file=sys.stderr)
            return
        
        #if not mapa.can_sail(new_pos[0], new_pos[1]):   #checks if its not a rock
        #    print("Invalid move: cannot sail there.", file=sys.stderr)
        #    return
        if any(s["pos"] == new_pos for sid, s in ship_dict.items() if sid != shipId):    #si hay algún ship ya con la misma pos, colision
            print(f"Move {command} for ship {shipId} is not possible due to own fleet collision.", file=sys.stderr)
            sys.stderr.flush()
            return
        print(f"Ship {shipId} new position: {new_pos}", file=sys.stderr)
        sys.stderr.flush()
    try:  
        os.write(shipId_dict["w_pipe"], f"{command}\n".encode())
        #envía el command (up, down, left, right) desde w_pipe. utiliza lo sel ship_dict pq necesita saber el id y todo del barco del q envía la info
        response = os.read(shipId_dict["r_pipe"], 1024).decode().strip() #recibe la respuesta del ship (Ok or NOK). 1024 es pq lee hasta 1024 bytes
    except OSError as e:
        print(f"Error happened: {e}", file=sys.stderr)
        return

    if response == "OK":  #ship moved to desired pos, everything correctly
        mapa.remove_ship(x, y)  #quita ell ship de dnd estaba antes
        mapa.set_ship(new_pos[0], new_pos[1])   #pone el ship en la posicion nueva
        shipId_dict["pos"] = new_pos  #actualiza la pos del ship en el dictionary
        shipId_dict["food"] -= 5  #actualiza el food en el dict (-5 pq se ha movido)
    elif response == "exit":   #eliminar zombie process
        os.waitpid(shipId_dict["pid"], 0)  #OS lo retiene hasta q el padre lo recibe para evitar zombies
        mapa.remove_ship(x, y)  #removes ship
        del shipId_dict[shipId]   #removes ship's ID from dictionary (ship is removed)
    elif response == "NOK":
        print("Ship stays in the same position.")


def print_status():
    for shipId, ship in ship_dict.items():
          if ship["pos"]:
            status = "Alive"
          else:
            status = "Terminated"

          print(f"Ship {shipId} {status} (PID: {ship['pid']}) At: {ship['pos']} "
              f"Food: {ship['food']} Gold: {ship['gold']}", file=sys.stderr)
          sys.stderr.flush()  # ensure output shows immediately

def main():
    args = arguments()  #parse arguments and prepare data
    global ursula_pipe
    ursula_pipe = args.ursula
    global mapa
    mapa = Map(args.map)    #to access to map (to know if collision with rocks)
    

    signal.signal(signal.SIGINT, handler_sigint)
    signal.signal(signal.SIGCHLD, handler_sigchld)

    print(f"Captain: {args.name} PID {os.getpid()}", file=sys.stderr)   #file=sys.stderr is to handle errors

    if ursula_pipe:
        send_to_ursula(f"{os.getpid()},INIT_CAPT", ursula_pipe)

    fileShips = read_ship_info(args.ships)  #get data from ships.txt
    children = []

    for shipId, x, y, speed in fileShips:    
        r_pipe, w_pipe = os.pipe()    #pipe to receive answers from ship
        cmd_r, cmd_w = os.pipe()      #pipe to send commands to ship
        try:         
            child = os.fork()
            #ships.append(shipId)   #for every shipID that is in the file, you add it to the list ship that you will use in the handlers
        except OSError as e:
                print(f"Error happened: {e}", file=sys.stderr)
                sys.exit(1)

        if child == 0:  #child process. En pipes, el hijo escribe y el padre lee
            try:
                #PIPES: 
                os.dup2(cmd_r, 0)   #reads orders from captain. 0 bc the stdin.
                os.dup2(w_pipe, 1)  #sends answers to captain. 1 is bc of the stdout.
                #if not using --> os.close()
                os.close(cmd_w)   #uses cmd_r
                os.close(r_pipe)  #uses r_pipe

                #execvp here bc if not, the process will be replaced
                cmd = [
                    "python3", "-u",
                    os.path.join(os.path.dirname(__file__), "ship5.py"),
                    "--id", str(shipId),
                    "--map", args.map,
                    "--pos", str(x), str(y),
                    "--captain",  # tells the ship to run in captain-controlled mode,
                    "--ursula", "ursula_pipe"
                ]
                os.execvp("python3", cmd)    #child executes ship.py, execvp replaces the process
            except OSError as e:
                print(f"Error happened: {e}", file=sys.stderr)
                sys.stderr.flush()
                sys.exit(1)
        else:  #parent process
            try:
                #print(f"Ship PID: {child}", file=sys.stderr)
                children.append((shipId, child))

                #PIPES
                #parent doesnt use os.dup2, only closes
                os.close(cmd_r)
                os.close(w_pipe)

                ship_dict[shipId] = {
                    "pid": child,
                    "pos": (int(x), int(y)),
                    "food": 100,
                    "gold": 0,
                    "w_pipe": cmd_w,
                    "r_pipe": r_pipe
                }
            except OSError as e:
                    print(f"Error happened: {e}", file=sys.stderr)
                    sys.exit(1)
    
    #SEND COMMANDS
    while ship_dict:   #while there are ships in the dictionary
        try:
            print("Enter command [exit | status | (Num, up/down/right/left/exit]:")
            #sys.stderr.flush()
            command = sys.stdin.readline().strip()
           # input("> ").strip()   #lee desde lo q se escribe en la terminal hasta el enter del usuario (up, down, lo q sea)
            # o command = input().strip()
            if command == "exit":
                print("Exiting and terminating all ships.", file=sys.stderr)
                sys.stderr.flush()
                handler_sigint(signal.SIGINT, None)   #se va a sigint pq está el os.kill y manda el sigQuit
            elif command == "status":
                print_status()
                sys.stderr.flush()
            else:
                #user enters [number, command] --> [1, up] --> ship 1 goes y += 1
                entered = command.split()   #divides btw shipId and cmd
                shipId, cmd = entered   #[1, up]
                send_command(shipId, cmd)
                sys.stderr.flush()

            alive = 0   
            #no vale len(ships) pq cuenta todos los barcos que han existido, vivos o muertos.
            for ship in ship_dict.values(): #searches for every ship in the dictionary that has a pos
                if ship.get("pos") is not None: #if that ship has a position (is alive)
                    alive += 1
            print(f"Number of ships alive: {alive}\n", file=sys.stderr)
            sys.stderr.flush()
        except OSError as e:
            print(f"Error happened: {e}", file=sys.stderr)
            sys.exit(1)
        
    for shipId, child in children:              #wait for each child in stored list
            waited_pid, status = os.waitpid(child, 0)
            exit_status = os.WEXITSTATUS(status)
            print(f"Ship {shipId}, with pid {waited_pid} finished with status {exit_status}", file=sys.stderr)
            sys.stderr.flush()

    
if __name__ == "__main__":
    main()

#python3 captain1.py --map ./map.txt --ships ships.txt


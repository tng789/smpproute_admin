import argparse
import getpass
import Pyro5.api
import json
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

class Commands(object):
    def __init__(self, smpp_manager):
        self.smpp_manager = smpp_manager
        self.cmd_set = {"login":self.login,
                        "help":self.help,
                        "dump":self.dump, 
                        "load":self.load,
                        "list":self.list,
                        "quit":self.quit,
                        "enable":self.enable,
                        "disable":self.disable
        }
        self.logged_in, self.session_id = self.login()

    def _is_senderid_available(self, sender_id):
        if not sender_id:
            print("sender_id not specified")
            return False, None                #if available, return True and the configs
                                                   #otherwise return False and None
        
        configs = self.smpp_manager.download(self.session_id, sender_id)
        return True, configs 

    def enable(self, *args):
        sender_id = args[0].rstrip().lstrip() if args else None

        available, configs = self._is_senderid_available(sender_id)

        if available and configs:
            configs["enabled"] = 3                  #deduct 1 for every unsuccessful attempt until 0 
            self.smpp_manager.update(self.session_id, sender_id, configs)

            
    def disable(self, *args):
        sender_id = args[0].rstrip().lstrip() if args else None

        available, configs = self._is_senderid_available(sender_id)

        if available and configs:
            configs["enabled"] = 0
            self.smpp_manager.update(self.session_id, sender_id, configs)

    def help(self):
            print("help message...")
    
    def login(self):
    
        retry = 3
        while retry > 0:
            user = ""
            while not user: user = input("user:")
            password = getpass.getpass("password:")
            result, sid = self.smpp_manager.authenticate(user, password)
            if result : 
                print(f"you are successfully logged in, session id is {sid}")
                return True, sid
            else:
                print("Auth failed. try again...")
                retry -= 1
        print("you have no more retry chances, bye!")
        return False, None

    def list(self, *gateway):
        # print(f"{len(gateway)=}")
        if len(gateway)== 0:

            files = self.smpp_manager.download_all(self.session_id)
            print(f"available gateways: {json.loads(files)}")
        else: #len(gateway) >= 1:
            config = self.smpp_manager.download(self.session_id, gateway[0])
            if  config == None:
                print(f"no route information for {gateway[0]}")
                return
            print(f"route information for {gateway[0]}:")
            print(json.dumps(config, indent=4, sort_keys=True))

    def load(self, *config_file):
        if not config_file:
            route_file_name = input("file name not specified, please enter the file name: ")
            real_file = route_file_name.rstrip().lstrip()
            if not real_file: 
                return
        else:
            real_file = config_file[0]

        try:
            with open(real_file,"rt") as f:
                configs = json.load(f)
        except Exception as e:
            print(f"error occurred {e}")
            return

        print(f"routes loaded from file {real_file}")
        print(json.dumps(configs, indent=4, sort_keys=True)) 
        
        sender_id =configs['user']
        if not sender_id:
            print("no sender_id found in the config file, please check the file")
            return

        print(f"the sender_id is {sender_id}")
        
        line = input(f"to replace the configs of {sender_id} with above setting? [No]")
        line = line.rstrip().lstrip()
        if not line or line.lower().startswith("n"):
            print("loaded routes discarded")
        else:
            # self.routes = configs.copy()
            self.smpp_manager.update(self.session_id, sender_id, configs)

    
    def dump(self, *args):
        if not args: 
            print("please specify the sender_id ")
            return
        
        sender_id = args[0].rstrip().lstrip()
        route_file = f"{sender_id}.json"
        configs = self.smpp_manager.download(self.session_id, sender_id)

        try:
            with open(route_file, "wt") as f:
                json.dump(configs, f, indent=4, sort_keys=True )
                print(f"The route information is saved into {route_file}")
        except Exception as e:
            print(f"error occurred {e}")
    
    
    def quit(self,*args):

        print(f"closing session {self.session_id}")
        self.smpp_manager.quit(self.session_id)

    def command_loop(self):
        session = PromptSession(">>> ", history=FileHistory(Path.home()/".command_history.txt"))

        while True:
            try:
                cmd_line = session.prompt()
                cmd_line = cmd_line.rstrip().lstrip().split()
                if not cmd_line: continue
        
                cmd, *args = cmd_line
                cmd = cmd.lower()
        
                if cmd.lower() not in self.cmd_set:
                    print(f"cmd {cmd} not recognized")
                else:            
                    self.cmd_set[cmd.lower()](*args)
            
                if cmd == "quit": break
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except EOFError:
                print("\nExiting via Ctrl+D...")
                break

#    def command_loop(self):
#
#        print("you are successfully authenticated,\nplease input your command, type help to list the commands ")
#
#        while True:
#            cmd_line = input(">>>")
#            cmd_line = cmd_line.rstrip().lstrip().split()
#            if not cmd_line: continue
#        
#            cmd, *args = cmd_line
#        
#            if cmd not in self.cmd_set:
#                print(f"cmd {cmd} not recognized")
#            else:            
#                self.cmd_set[cmd](*args)
#            
#            if cmd == "quit":
#                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--server", type=str, default="localhost", help="the server hosting the smpp application")
    parser.add_argument("--port", type=int, default=9090, help="the port of smpp server host")
    parser.add_argument("--service", type=str, default="smpp_server", help="the port of smpp server host")
    opt = parser.parse_args()

    try:
        ns = Pyro5.api.locate_ns(host = opt.server, port=opt.port)
        uri =ns.lookup(opt.service)
        smpp_manager = Pyro5.api.Proxy(uri)
        print(f"server found {smpp_manager}")
    except Exception as e:
        print(f"error occurred {e}")
        exit()

    Commands(smpp_manager).command_loop()
    
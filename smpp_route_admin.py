import json
import os
from smpp_logger import get_logger
import uuid

import Pyro5.api
import Pyro5.nameserver

from pathlib import Path
import threading
import argparse
import requests

users = { "admin":"admin7890"}
prefix = ".smppcfg"
service_url = "https://ipinfo.io/ip"
# 模拟用户会话，存储已登录用户

@Pyro5.api.expose
class smpp_manager(object):
    sessions = []
    def __init__(self):
        self.active_sessions = dict()
        self.logged_in_users = set()
        self.route = None

    def authenticate(self, username, password):

        if username in users and users[username] == password:
            logger.info(f"{username} logged in")
            if username in self.logged_in_users:
                return False, "Already logged in"
            else:
                session_id = str(uuid.uuid4())
                self.active_sessions[session_id] = username
                return True, session_id
        return False,"username or password wrong"

#    def get_user_info(self, username):
#        if username in logged_in_users:
#            return f"欢迎，{username}！你的信息已获取。"
#        return "请先登录。"
    
    def quit(self,sid):

        if sid in self.active_sessions:
            # print("in active_sessions")
            username = self.active_sessions[sid]
            logger.info(f"{username} log out")
            self.active_sessions.pop(sid)
        if username in self.logged_in_users:
            self.logged_in_users.remove(username)
            
        return True

    def download(self, sid, channel):
        config = Path.home() / prefix / f"{channel}.json"
        if not config.exists():
            logger.error(f"Configuration file {config} does not exist.")
            return None
        with open(config, "rt") as f:
            try:
                smpp_routes = json.load(f)
                self.route= smpp_routes
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from {config}: {e}")
                return None
            
        if sid in self.active_sessions:
            logger.info(f"smpp route {channel} info downloaded...")
            return self.route
        else:
            return None

    def update(self, sid, sender_id, route):
        if sid not in self.active_sessions:
            return False

        config_file = Path.home() / prefix / f"{sender_id}.json"

        with open(config_file,"wt") as f:
            json.dump(route,f,indent=4)
        logger.info(f"smpp route {sender_id} info downloaded...")
        return True

    def download_all(self, sid):
        directory = Path.home() / prefix 
        # print(directory)
        json_files = []

        if not directory.exists():
            logger.error(f"Configuration file {directory} does not exist.")
            # return []
        else:
            json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
        return json.dumps(json_files)
        # path = Path(directory)
        # l =  list(path.glob('*.json'))
        # return json.dumps(list(path.glob('*.json')))

def get_public_ip():
    
    try:
        response = requests.get(service_url, timeout=5)
        if response.status_code == 200:
            return response.text.strip()
        else:
            print(f"Error: Received status code {response.status_code}")
            return ""
    except requests.RequestException as e:   
        print(f"Error: {e}")
        return ""

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--server", type=str, help="the IP of the server wheere the naming service is running")
    parser.add_argument("--nport", type=int, default=9090, help="the port of naming service")
    parser.add_argument("--dport", type=int, default=10101, help="the port of daemon exposing")
    parser.add_argument("--service", type=str, default="smpp_server", help="the name of the service")
    opt = parser.parse_args()

    exposure = get_public_ip()
    if not exposure:
        print("Failed to get public IP address, exiting...")
        exit(1)

    # 启动命名服务
    if not opt.server:
        print("IP not specified, exiting...")
        exit(1)

    logger = get_logger("route_admin")
    ns_thread = threading.Thread(
        target=Pyro5.nameserver.start_ns_loop,
        kwargs={"host": opt.server,  "port": opt.nport,"nathost": exposure, "natport": opt.nport},
        daemon=True
    )
    ns_thread.start()
    logger.info(f"Pyro5 Name Server started at {opt.server}:{opt.nport}...")

    import time
    time.sleep(1)  # 等待命名服务启动
    daemon = Pyro5.api.Daemon(host=opt.server, port=opt.dport, nathost=exposure, natport=opt.dport,)  # 使用指定的IP

    ns = Pyro5.api.locate_ns(opt.server, opt.nport)
    if not ns:
        logger.error("Failed to locate the Name Server.")
        exit(1)
    uri = daemon.register(smpp_manager())
 
    ns.register(opt.service, uri)

    logger.info("smpp routes admin is Ready.")
    daemon.requestLoop()
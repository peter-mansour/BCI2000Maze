
import socket
import threading
import queue
import pickle
from connect_utils import *
from GameLogic import *
import os
import zlib
import json
from json import JSONEncoder
import logging
import binascii

if not os.path.isdir('../logs'):
    os.makedirs('../logs')
with open('../logs/tcpserv.log', 'w'):
    pass
log_tcpserv = logging.getLogger(__name__)
log_tcpserv.setLevel(logging.INFO)
handler_f = logging.FileHandler('../logs/tcpserv.log')
handler_f.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s'))
log_tcpserv.addHandler(handler_f)

class TCPServer:
    BUFFER_SZ = 10000
    __MSG_JOIN = "%s joined the network"
    __MSG_REQ = "%s requested to be a %s"
    __MSG_WELCOME = "Server is Up and Running..."
    __HOW2CLOSE = "Ctrl + C to close Server"
    __MSG_FORWARDP = "forwarding pkt to %s (%s) with transaction ids %s and requests %s"
    __MSG_FORWARDJ = "forwarding pkt to %s (%s) with requests %s"
    __MSG_LEFT = "%s left the network"
    __MSG_REJECT_JOIN = "Rejected %s request to join (already on network)"
    __MSG_RCV_JSON = 'json pkt received from %s with request %s'
    __MSG_RCV_PICK = 'pickle pkt received from %s with request %s'
    __clients = []
    __players = []
    __listeners = []
    __ready_pkgs = queue.Queue()
    __trig_ready = threading.Event()
    __trig_process = threading.Event()
    __pkt_buffer = queue.Queue()
    __broadcast_buff = queue.Queue()
    __broadcast_item = threading.Event()
    __player_count = 0
    __game_on = False
    __threads = {0: None}
    __destroy_threads = queue.Queue()
    __cleanup = threading.Event()
    __manager_t = None
    _shutdown = False
    __sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    __MAX_MSGS = 50
    __byte_delim = b'?_?'
    
    @staticmethod
    def init(IP, PORT, count, inos):
        TCPServer.__IP = IP
        TCPServer.__PORT = PORT
        TCPServer.__player_count = count
        TCPServer.__inos = inos
        TCPServer.__run_host_t = threading.Thread(target=TCPServer.__run_host, args=(), daemon=True)
        TCPServer.__manager_t = threading.Thread(target=TCPServer.__manage_threads, args=(), daemon=True)
        TCPServer.__process_pkt_t = threading.Thread(target=TCPServer.__process_pkt, args=(), daemon=True)
        TCPServer.__broadcast_t = threading.Thread(target=TCPServer.broadcast, args=(TCPServer.__broadcast_buff, 
        TCPServer.__broadcast_item), daemon=True)
        TCPServer.__threads.update({os.urandom(8):TCPServer.__run_host_t, os.urandom(8):TCPServer.__manager_t, 
            os.urandom(8):TCPServer.__process_pkt_t, os.urandom(8):TCPServer.__broadcast_t})

    @staticmethod
    def run_host():
        TCPServer.__sock.bind((TCPServer.__IP, TCPServer.__PORT))
        TCPServer.__run_host_t.start()
    
    @staticmethod
    def __run_host():
        print(TCPServer.__MSG_WELCOME, flush=True)
        print(TCPServer.__HOW2CLOSE)
        log_tcpserv.info(TCPServer.__MSG_WELCOME)
        TCPServer.__manager_t.start()
        TCPServer.__process_pkt_t.start()
        TCPServer.__broadcast_t.start()
        TCPServer.__sock.listen(1)
        try:
            while not TCPServer._shutdown:
                sock, (ip, ext) = TCPServer.__sock.accept()
                client = ClientInfo(sock, ip, ext)
                if not TCPServer.on_network(client):
                    TCPServer.__clients.append(client)
                    log_tcpserv.info(TCPServer.__MSG_JOIN % client.ip)
                    thid = os.urandom(8)
                    client_th = threading.Thread(target=TCPServer.__talk2client, args=(client, thid), daemon=True)
                    client_th.start()
                    TCPServer.__threads.update({thid:client_th})
                else:
                    log_tcpserv.warning(TCPServer.__MSG_REJECT_JOIN % client.ip)
        except KeyboardInterrupt as e:
            TCPServer.__manager_t.join()
            raise e
    
    @staticmethod
    def __json2dict(str):
        try:
            return json.loads(str)
        except ValueError:
            return None
    
    @staticmethod
    def __ascii2str(asci):
        try:
            return asci.decode('ascii')
        except UnicodeDecodeError:
            return None
    
    @staticmethod
    def __talk2client(client, thid):
        try:
            while not TCPServer._shutdown:
                p = client.sock.recv(TCPServer.BUFFER_SZ)
                if p:
                    pkts = p.split(TCPServer.__byte_delim)
                    for pkt in pkts:
                        pkt_str = TCPServer.__ascii2str(pkt)
                        if pkt_str:
                            pkt_content = TCPServer.__json2dict(pkt_str)
                            TCPServer.__pkt_buffer.put((pkt_content, 'json', client), block=True)
                            log_tcpserv.info(TCPServer.__MSG_RCV_JSON %(client.ip, pkt_content['request']))
                        else:
                            pkt_info = pickle.loads(pkt)
                            TCPServer.__pkt_buffer.put((pkt_info, 'pickle', client), block=True)
                            log_tcpserv.info(TCPServer.__MSG_RCV_PICK %(client.ip, pkt_info.request))
                        TCPServer.__trig_process.set()
                else:
                    TCPServer.remove(client)
                    break
            client.sock.close()
        except (ConnectionResetError, EOFError):
            TCPServer.remove(client)
        TCPServer.__destroy_threads.put(thid, block=True)
        TCPServer.__cleanup.set()
    
    @staticmethod
    def __manage_threads():
        while TCPServer.__cleanup.wait():
            thid = TCPServer.__destroy_threads.get(block=True)
            TCPServer.__threads[thid].join()
            if TCPServer.__destroy_threads.empty():
                TCPServer.__cleanup.clear()
    
    @staticmethod
    def __process_pkt():
        st_offset = 0
        while TCPServer.__trig_process.wait():
            if not TCPServer.__pkt_buffer.empty():
                pkt_info = TCPServer.__pkt_buffer.get(block=True)
                if pkt_info[1] == 'json' and pkt_info[0]['request'] == '_x_watch_x_':
                    pkt_info[2].role = 'Listener'
                    TCPServer.__listeners.append(pkt_info[2])
                    log_tcpserv.info(TCPServer.__MSG_REQ % (pkt_info[2].ip, 'Listener'))
                elif pkt_info[1] == 'pickle':
                    client = TCPServer.get_client(pkt_info[0].id_from['ip'], TCPServer.__clients)
                    if pkt_info[0].request == '_x_play_x_':
                        client.role = 'Player'
                        client.clr = pkt_info[0].id_from['clr']
                        client.misc = pos(GameLogic._start_pos[0]+st_offset, GameLogic._start_pos[1], 0, 0, 90, None)
                        st_offset+=4
                        for ino in TCPServer.__inos:
                            client.ino = (ino[0], ino[1]) if ino[2] else None
                        TCPServer.__players.append(client)
                        TCPServer.dm(client, Pkt('_x_img_x_', {'ip':'0.0.0.0', 'clr':None}, 
                            {'ip':'0.0.0.0', 'clr':None}, {'ip':'0.0.0.0', 'clr':None}, 
                            zlib.compress(ImageProcessing.img2base64(GameLogic._maze_img_obj)), 
                            None, os.urandom(8), None, None))
                        rsp = Pkt('_x_new_player_x_', {'ip':client.ip, 'clr':client.clr}, {'ip':'0.0.0.0', 'clr':None}, 
                            {'ip':client.ip, 'clr':client.clr}, None, None, os.urandom(8), client.misc, None)
                        TCPServer.__broadcast_buff.put((rsp, 'pickle'), block=True)
                        TCPServer.__broadcast_item.set()
                        for p in TCPServer.__players:
                            if p.ip != client.ip:
                                TCPServer.dm(client, Pkt('_x_new_player_x_', {'ip':'0.0.0.0', 'clr':None}, 
                                    {'ip':'0.0.0.0', 'clr':None}, {'ip':p.ip, 'clr':p.clr}, 
                                    None, None, os.urandom(8), p.misc, None))
                        log_tcpserv.info(TCPServer.__MSG_REQ % (client.ip, 'Player'))
                    elif pkt_info[0].request == '_x_gameplay_x_' and client.role == 'Player' and TCPServer.__game_on:
                        new_pos = client.misc
                        warn = None
                        try:
                            new_pos, dir, win = GameLogic.update_pos(client.ip, client.misc, pkt_info[0].data)
                        except OutOfBounds as e:
                            win = None
                            dir = None
                            warn = "%s (%d, %d)" % (e.msg, e.x, e.y)
                        rsp_pick = Pkt('_x_gameplay_x_', {'ip':client.ip, 'clr':client.clr}, {'ip':'0.0.0.0', 'clr':None}, 
                            {'ip':client.ip, 'clr':client.clr}, None, None, os.urandom(8), new_pos, warn)
                        rsp_json = PktCompact('_x_gameplay_x_', client.ip, client.clr, dir, new_pos.deg)
                        TCPServer.__broadcast_buff.put((rsp_json, 'json'), block=True)
                        TCPServer.__broadcast_buff.put((rsp_pick, 'pickle'), block=True)
                        TCPServer.__broadcast_item.set()
                        if dir and client.ino:
                            client.ino[1].put(dir, block=True)
                        if win:
                            TCPServer.dm(client, Pkt('_x_img_x_', {'ip':'0.0.0.0', 'clr':None}, {'ip':'0.0.0.0', 'clr':None}, 
                            {'ip':client.ip, 'clr':client.clr}, zlib.compress(ImageProcessing.img2base64(GameLogic._win_img)), 
                            None, os.urandom(8), None, None))
                            for c in TCPServer.__players:
                                if c.ip != client.ip:
                                    TCPServer.dm(c, Pkt('_x_img_x_', {'ip':'0.0.0.0', 'clr':None}, 
                                        {'ip':'0.0.0.0', 'clr':None}, {'ip':client.ip, 'clr':client.clr}, 
                                        zlib.compress(ImageProcessing.img2base64(GameLogic._lose_img)), 
                                        None, os.urandom(8), None, None))
                            TCPServer._shutdown = True
                            TCPServer.__game_on = False
                            break
                    elif pkt_info[0].request == '_x_keyboard_x_' and client.role == 'Player':
                        GameLogic._bind_keys(client.ip, pkt_info[0].data)
                    elif pkt_info[0].request == '_x_ready_x_' and client.role == 'Player':
                        if TCPServer.__game_on:
                            rsp = Pkt('_x_start_x_', {'ip':'0.0.0.0', 'clr':None}, {'ip':'0.0.0.0', 'clr':None},
                                None, None, None, os.urandom(8), None, None)
                            TCPServer.dm(client, rsp)
                        else:
                            TCPServer.__ready_pkgs.put(pkt_info[0])
                            TCPServer.__trig_ready.set()
            if TCPServer.__pkt_buffer.empty():
                TCPServer.__trig_process.clear()

    @staticmethod
    def _wait():
        kill = threading.Event()
        ready_t = threading.Thread(target=TCPServer.__ready_up, args=(kill,), daemon=True)
        ready_t.start()
        if kill.wait():
            ready_t.join()
    
    def __ready_up(kill):
        ips = []
        while TCPServer.__trig_ready.wait() and len(ips) < TCPServer.__player_count:
            if not TCPServer.__ready_pkgs.empty():
                pkt = TCPServer.__ready_pkgs.get(block=True)
                if pkt.request == '_x_ready_x_':
                    try:
                        index = ips.index(pkt.id_from['ip'])
                    except ValueError:
                        index = -1
                    if index == -1:
                        ips.append(pkt.id_from['ip'])
        rsp = Pkt('_x_start_x_', {'ip':'0.0.0.0', 'clr':None}, {'ip':'0.0.0.0', 'clr':None},
            None, None, None, os.urandom(8), None, None)
        TCPServer.__broadcast_buff.put((rsp, 'pickle'), block=True)
        TCPServer.__broadcast_item.set()
        TCPServer.__game_on = True
        kill.set()
            
    @staticmethod
    def broadcast(buff, trigger):
        while trigger.wait():
            msg_sz_j = 0
            msg_sz_p = 0
            json_msg = b''
            byte_msg = b''
            requests_json = ''
            requests_pickle = ''
            txns_pickle = ''
            while not buff.empty() and msg_sz_j < TCPServer.__MAX_MSGS and msg_sz_p < TCPServer.__MAX_MSGS:
                pkt_info = buff.get(block=True)
                if pkt_info[1] == 'json':
                    if json_msg:
                        json_msg+=TCPServer.__byte_delim
                    json_msg+=json.dumps(pkt_info[0], cls=PktJsonEncoder).encode('ascii')
                    requests_json+=(pkt_info[0].request + ' ')
                    msg_sz_j+=1
                elif pkt_info[1] == 'pickle':
                    if byte_msg:
                        byte_msg+=TCPServer.__byte_delim
                    byte_msg+=pickle.dumps(pkt_info[0])
                    requests_pickle+=(pkt_info[0].request + ' ')
                    txns_pickle+=(str(binascii.hexlify(pkt_info[0].txn)) + ' ')
                    msg_sz_p+=1
            if json_msg:
                for l in TCPServer.__listeners:
                    l.sock.send(json_msg)
                    log_tcpserv.info(TCPServer.__MSG_FORWARDJ % (l.ip, l.role, requests_json))
            if byte_msg:
                for p in TCPServer.__players:
                    p.sock.send(byte_msg)
                    log_tcpserv.info(TCPServer.__MSG_FORWARDP % (p.ip, p.role, txns_pickle, requests_pickle))
            trigger.clear()

    @staticmethod
    def dm(user, pkt, serial_method='pickle'):
        if serial_method == 'json':
            user.sock.send(json.dumps(pkt, cls=PktJsonEncoder).encode('ascii'))
        elif serial_method == 'pickle':
            user.sock.send(pickle.dumps(pkt))
        log_tcpserv.info(TCPServer.__MSG_FORWARDP % (user.ip, user.role, 
            binascii.hexlify(pkt.txn), pkt.request))
    
    @staticmethod
    def on_network(client):
        for c in TCPServer.__clients:
            if c.ip == client.ip:
                return True
        return False
    
    @staticmethod
    def get_client(ip, clients):
        for c in clients:
            if c.ip == ip:
                return c
        return None
    
    @staticmethod
    def remove(client):
        log_tcpserv.info(TCPServer.__MSG_LEFT % client.ip)
        for c in TCPServer.__clients:
            if c.ip == client.ip:
                TCPServer.__clients.remove(c)
                if c in TCPServer.__listeners:
                    TCPServer.__listeners.remove(c)
                if c in TCPServer.__players:
                    TCPServer.__players.remove(c)
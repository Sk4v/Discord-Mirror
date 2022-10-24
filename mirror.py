import websocket
import json
import threading
import time
import requests
import schedule
import termcolor
import logging
from datetime import datetime


def send_json_request(ws,request):
    ws.send(json.dumps(request))

def receive_json_response(ws):
    response = ws.recv()
    if response: return json.loads(response)

def hearbeat(interval,ws):
    print('Heartbeat begin')
    while True:
        try:
            time.sleep(interval)
            hearbeatJson = {
                "op":1,
                "d": "null"
            }
            send_json_request(ws,hearbeatJson)
            print('Heartbeat sent')
            pong = receive_json_response(ws)
            print(termcolor.colored(pong,'red'))
        except Exception as e: print(termcolor.colored(e,'yellow'))


def edit_embed(event):
    try:
        if event['d']['embeds']==[]: return None
        else:
            embed = event['d']['embeds'][0]
            return embed
    except: return None

def readjson():
    with open('mirror-info.json', "r") as jsonFile:
        data = json.load(jsonFile)

    token = data['token']
    d = data['channel-webhook']
    print(d)
    print(type(d))

    return token,d

def connection():
    discordws = "wss://gateway.discord.gg/?v=9&encoding=json"
    ws = websocket.WebSocket()
    ws.connect(discordws)
    return ws

def auth(ws,token):
    payload = {
        "op": 2,
        "d": {
            "token": token,
            "properties": {
                "$os": "windows",
                "$browser": "chrome",
                "$device": "pc"
            },
            "presence": {
                "status": "dnd"
            }

        }# "shards":9
    }
    send_json_request(ws, payload)

def resume(ws,token,session_id,last_seq):
    #try:
    payload = {
      "op": 6,
      "d": {
            "token": token,
            "session_id": session_id,
            "seq": last_seq
      }
    }
    send_json_request(ws, payload)
    #except:
     #   auth()

def main():

    '''Inizializzazione del logger'''
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # or whatever
    handler = logging.FileHandler('mirror.log', 'w', 'utf-8')
    root_logger.addHandler(handler)

    '''Inizializzazione informazioni utente'''
    info = readjson()
    token = info[0]
    d = info[1]

    '''Connessione al websocket'''
    ws = connection()
    event = receive_json_response(ws)
    print('First event: ', event)

    '''Heartbeat Thread'''
    hearbeat_interval = event['d']['heartbeat_interval'] /1000
    threading._start_new_thread(hearbeat,(hearbeat_interval,ws))


    '''Auth con il websocket'''
    auth(ws, token)

    retry = 0
    while True:
        try:

            event = receive_json_response(ws)
            print('event: ', event)
            if event == None: pass
            else:

                if event['t'] == 'READY' or event['t'] == 'SESSIONS_REPLACE':
                    try:session_id = event['d']['sessions'][0]['session_id']
                    except: session_id=None
                    #print(session_id)
                #print(f'{event["d"]["author"]["username"]}: {event["d"]["content"]}')
                if event['s'] != None:
                    last_sequence = event['s']
                    #print(last_sequence)

                op_code = event['op']

                if op_code == 1:
                    hearbeat(hearbeat_interval,ws)
                    # client deve inviare un heartbeat opcode 1


                if op_code == 7:
                    try:
                        print(termcolor.colored('TRY TO RESUME LAST SEQUENCE...', 'red'))
                        resume(ws, token, session_id, last_sequence)
                    except:
                        auth(ws, token)
                        print(termcolor.colored('TRY TO RECONNECT...', 'red'))
                        retry += 1
                        root_logger.info('N. Connection: ' + str(retry) + ' ' + str(datetime.now()))


                if op_code == 9:
                    ws = connection()
                    auth(ws, token)
                    print(termcolor.colored('SESSION NOT VALID...new connection', 'red'))
                    retry += 1
                    root_logger.info('N. Connection: ' + str(retry) + ' ' + str(datetime.now()))

                if op_code == 11:
                    print('heartbeat received')

                #    send_json_request(ws, payload)

                try: channel_id = event['d']['channel_id']
                except: channel_id = None

                if channel_id != None and channel_id in d:
                    embed = edit_embed(event)
                    if embed!=None:
                        data = {#'username': 'BOT TRACKER',
                                'embeds': [embed]}
                        requests.post(d[channel_id], json=data)
                    else:
                        try: messaggio = event["d"]["content"]
                        except: messaggio=None
                        print('messaggio: ', messaggio)
                        if messaggio !=None: #and messaggio in ['@here','@everyone']:
                            data = {'content': messaggio}
                            requests.post(d[channel_id], json=data)

        except websocket._exceptions.WebSocketConnectionClosedException:
            ws.close()
            ws = connection()
            auth(ws,token)
            print(termcolor.colored('TRY TO RECONNECT...', 'red'))
            retry += 1
            root_logger.info('N. Connection: ' + str(retry) + ' ' + str(datetime.now()))


        finally: pass



if __name__ == '__main__':
    main()

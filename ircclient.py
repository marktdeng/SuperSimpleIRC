'''
An IRC Client

By Mark Deng 
21-02-2014
'''

import socket
import time
import sys
import threading

class IRCClient(threading.Thread):
    connected = False
    loop = True
    
    def __init__(self,lock, server, port, channels, nickname, password = ''):
        threading.Thread.__init__(self)
        self.server = server
        self.port = port
        self.nickname = nickname
        self.channels = channels
        self.password = password
        self.socket = socket.socket()
        self.lock = lock
        self.starttime = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
        
    def run(self):
        self.socket.connect((self.server, self.port))
        if self.password != '':
            self.send('PASS %s' % self.password)    # Send password if one is given
        self.send('NICK %s' % self.nickname)        # Send Nickname
        self.send('USER %(nick)s %(nick)s %(nick)s :%(nick)s' % {'nick':self.nickname})
        
        while self.loop == True:
            packet = self.socket.recv(4096)     # Receive data
            lines = packet.split('\n')          # Split data into lines
            for data in lines:
                data = str(data).strip()        
                if data == '':                  # Ignore data if empty
                    continue
                if data.find('PING') != -1:
                    with self.lock:
                        print '<--',data
                    n = data.split(':')[1]
                    self.send('PONG :' + n)
                        
                parts = data.split(' ', 3)
                if len(parts) != 4:
                    continue

                message = {}
                message['sender'] = parts[0][1:].split('!',1)[0]
                message['type']   = parts[1]
                message['target'] = parts[2]
                message['msg']    = parts[3][1:].strip()
                
                if self.connected == False:
                    self.connectedServer = message['sender']
                    
                if message['sender'] == self.connectedServer and message['target'] == self.nickname:    # Server sent me a message
                    with self.lock:
                        print '***',message['type'],':',message['msg']
                
                elif message['type'] == 'QUIT':                                                         # A user quit
                    with self.lock:
                        print '***',message['sender'],'left %s (%s)' % message['target'], message['msg']
                
                elif message['type'] == 'KICK' and message['msg'].split(':',1)[1] == self.nickname:     # You were kicked from a channel
                    with self.lock:
                        print '***',message['sender'],'kicked you from',message['target']
                    self.channels.remove(message['target'])
                    
                    
                elif message['type'] == 'PRIVMSG' and message['target'] == self.nickname:           # Someone messaged you
                    query = message['msg'].lower()
                    with self.lock:
                        print '<-- [Whispher]',message['sender'].split('!')[0],':',message['msg']
                    if query == 'ping':
                        self.say('pong', message['sender'])
                    elif query == 'info':
                        self.say('Up Since: %s' % self.starttime, message['sender'])

                elif message['type'] == 'PRIVMSG' and message['target'][0] == '#':           # Someone sent a message to a channel i am in
                    with self.lock:
                        print '<--',message['sender'],message['target'],':',message['msg']
                else:
                    with self.lock:
                        print '<--',message['sender'],message['type'],message['target'],':',message['msg']
                
                if self.connected == False:
                    self.login()
                    self.connected = True
                    
                
    def send(self, msg):        # Send message to server
        print '-->',msg
        self.socket.send(msg+'\r\n')
        
    def say(self, msg, to):     # Send message to someone
        self.send('PRIVMSG %s :%s' % (to, msg))
        
    def sayall(self, msg):      # Send message to all joined channels
        for c in self.channels:
            self.say(msg,c)
        
    def login(self):
        self.send('PRIVMSG R : Login <>')
        self.send('MODE %s +x' % self.nickname)
        for c in self.channels:     # Join channels
            self.send('JOIN %s' % c)
        
def main():
    if len(sys.argv) != 4:      # Check for correct number of args
        print('Usage: IRCClient <server[:port]> <nickname[:password]> <channel1:channel2...>')
        sys.exit(1)
    s = sys.argv[1].split(':', 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            print("Error: Erroneous port.")
            sys.exit(1)
    else:
        port = 6667
    channels = sys.argv[3].split(':')
    n = sys.argv[2].split(':', 1)
    nickname = n[0]
    if len(n) == 2:
        password = n[1]
    else:
        password = ''
    lock = threading.Lock()
    IRC = IRCClient(lock,server,port,channels,nickname,password)
    IRC.daemon = True
    IRC.start()
    while True:
        raw_input()         # Press enter before entering text
        with lock:          # Prevent thread from printing while inputting
            r = raw_input('--> ')
            if r != '':
                if r[0] == '/':
                    m = r.split('/',1)[1]
                    c = m.split(' ',1)
                    if c[0].upper() == 'QUIT':
                        sys.exit(0)
                    elif len(c) == 2:
                        IRC.send(c[0].upper() + ' ' + c[1])     # Send command to server
                    else:
                        IRC.send(c[0].upper())
                    if c[0].upper() == 'JOIN' and len(c) == 2:  
                        for channel in c[1].split():
                            if channel in IRC.channels:
                                print 'Already joined %s' % channel
                            else:
                                IRC.channels.append(channel)    # Add joined channels to list of channels
                                print 'joined %s' % channel
                    
                else:
                    m = r.split(':', 1)
                    if len(m) == 2:
                        IRC.say(m[1].strip(),m[0])
                    else:
                        IRC.sayall(r)
                
if __name__ == '__main__':
    main()
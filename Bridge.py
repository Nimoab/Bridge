import socket
import signal
import select
import threading
import argparse

## =========================================================================== 
## Bridge class
## =========================================================================== 
class Bridge:

    ## ======================================================================= 
    ## ======================================================================= 
    def __init__(self, lHost, lPort, sHost, sPort):

        self._interrupted = False
        self._lSocket     = socket.socket()
        self._mainWorker  = None
        self._sHost       = sHost
        self._sPort       = sPort

        self._lSocket.settimeout(0.5)
        self._lSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self._lSocket.bind((lHost, lPort))
        self._lSocket.listen()

    ## ======================================================================= 
    ## ======================================================================= 
    def interrupt(self):
        self._interrupted = True
        if self._mainWorker: self._mainWorker.join()

    ## ======================================================================= 
    ## ======================================================================= 
    def start(self, blocking = True):
        self._mainWorker = threading.Thread(target = self._acceptLoop)
        self._mainWorker.start()

        if blocking: self._mainWorker.join()

    ## ======================================================================= 
    ## ======================================================================= 
    def _acceptLoop(self):
        
        workers = []

        while not self._interrupted:
            try:
                comSocket, address = self._lSocket.accept()
            except socket.timeout:
                continue

            worker = threading.Thread(target = self._bridgeLoop,
                                      args   = (comSocket, address))
            worker.start()
            workers.append(worker)

        for worker in workers:
            worker.join()

        self._lSocket.close()

    ## ======================================================================= 
    ## ======================================================================= 
    def _bridgeLoop(self, lSocket, address):
        print_ = lambda m: print("[{:0>20d}:{}:{}] {}".\
                                 format(threading.get_ident(), * address, m))

        print_("New connection")
        sSocket = socket.socket()
        sSocket.connect((self._sHost, self._sPort))

        connectionClosed = False
        endMessage       = ""

        while not self._interrupted and not connectionClosed:

            rList, _, _ = select.select([lSocket, sSocket], [], [], 0.5)

            if len(rList) == 0: continue

            for srcSocket in rList:
                data = srcSocket.recv(1024)

                if len(data) == 0:
                    connectionClosed = True
                    endMessage       = "receiving"
                    break


                dstSocket = sSocket if srcSocket == lSocket else lSocket

                try:
                    dstSocket.sendall(data)
                except Exception as e:
                    connectionClosed = True
                    endMessage       = "sending ({})".format(str(e))
                    break

        if len(endMessage) == 0: endMessage = "interrupted"

        sSocket.close()

        print_("Connection closed - {}".format(endMessage))

## =========================================================================== 
## =========================================================================== 
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--l_host", required = True, type = str)
    parser.add_argument("--l_port", required = True, type = int)
    parser.add_argument("--s_host", required = True, type = str)
    parser.add_argument("--s_port", required = True, type = int)

    args = parser.parse_args()

    bridge = Bridge(args.l_host, args.l_port, args.s_host, args.s_port)

    signal.signal(signal.SIGINT, lambda *a,**k: bridge.interrupt())

    bridge.start()


import sys
import threading as th
import ctypes
from win_cmd import Console
import time

class Bar:
    
    def __init__(self, task, maxval):
        self.__bar = ''
        self.__bar_sz = 30
        self.__iter = 0
        self.__task = task
        self.__max_iter = maxval
        self.__progress_symbol = '#'
        self.__destroy = 0
        self.__trigger_draw = th.Event()
        self.__bar_t = th.Thread(target=self.__draw_bar, args=(self.__trigger_draw,), daemon=True)
        self.__bar_t.start()

    def update(self):
        self.__iter += 1
        self.__trigger_draw.set()
        if self.__iter == self.__max_iter:
            self.shutdown()
    
    def shutdown(self):
        time.sleep(1)
        print('', flush=True)
        self.__destroy = 1
    
    def __draw_bar(self, trigger):
        progress = 0
        percent = 0
        percent_sz = 1
        for i in range(self.__bar_sz):
            self.__bar+=' '
        Console.disable_quick_edit()
        sys.stdout.write("%s: " % self.__task)
        sys.stdout.write("[%s] %d%%" % (self.__bar, percent))
        sys.stdout.flush()
        
        while trigger.wait() and not self.__destroy:
            self.__bar = ''
            progress = round(self.__iter*self.__bar_sz/self.__max_iter)
            percent = round(self.__iter*100/self.__max_iter)
            for i in range(progress):
                self.__bar += self.__progress_symbol
            for j in range(progress, self.__bar_sz):
                self.__bar += ' '
            sys.stdout.write("\b"* (self.__bar_sz+4+percent_sz))
            sys.stdout.write("[%s] %d%%" % (self.__bar, percent))
            sys.stdout.flush()
            if percent >= 10 and percent <= 99:
                percent_sz = 2
            elif percent == 100:
                percent_sz = 3
            trigger.clear()
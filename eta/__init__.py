# originally from https://github.com/mbreese/eta/blob/master/eta/__init__.py
# modified by daijro to work better on windows


'''
Displays a progress meter and an ETA calculation based upon either a user supplied number (out of a total)
or based upon a file and it's size.  In the case of a file, the position information is calculated from the
tell() method.  The ETA is calculated by taking the average of the last 50 ETA calculations so that the numbers
can be smoothed out.  Additionally, you can set a 'modulo' parameter that will only display a message every
N iterations (thus relieving you from having to calculate it).

Marcus R Breese <marcus@breese.com>
Created: Jan 2010
Last update: Oct 2012

'''
import os
import sys
import datetime
import shlex
import struct
import platform
import subprocess
from colorama import Fore

def eta_open_iter(fname, callback=None):
    f = open(fname)  # not using with to support 2.4
    _eta = ETA(os.stat(fname).st_size, fileobj=f)
    extra = ''
    for line in f:
        if callback:
            extra = callback()
        _eta.print_status(extra=extra)
        yield line
    _eta.done()
    f.close()


class _NoopETA(object):
    def __init__(self, *args, **kwargs):
        pass

    def done(self):
        pass

    def print_status(self, *args, **kwargs):
        pass


class _ETA(object):
    def __init__(self, total, modulo=None, fileobj=None, window=50, step=1, prog_bar_length=20, min_ms_between_updates=None):
        self.started = datetime.datetime.now()
        self.last = []
        self.total = total
        self.spinner = "|/-\\"
        self.spinner_pos = 0
        self.i = 0
        self.modulo = modulo

        try:
            fileobj.fileobj.tell()
            self.fileobj = fileobj.fileobj
        except:
            self.fileobj = fileobj

        self.last_len = 0
        self.step = step
        self.last_step = 0
        self.window = window
        self.prog_bar_length = prog_bar_length
        
        if min_ms_between_updates is not None:
            self.min_ms_between_updates = min_ms_between_updates  # in milliseconds
        elif sys.stderr.isatty():
            self.min_ms_between_updates = 200
        else:
            self.min_ms_between_updates = 10000

        self._last_update = 0
        self._started = 0

    def pct(self, current):
        if current < self.total:
            return float(current) / self.total
        return 1

    def ave_remaining(self, current, elapsed_sec):
        if len(self.last) > self.window:
            self.last = self.last[-self.window:]
        rem = self.remaining(current, elapsed_sec)
        if rem:
            self.last.append(rem)

        acc = 0.0
        for p in self.last:
            acc += p

        if len(self.last) > 0:
            return acc / len(self.last)
        else:
            return None

    def remaining(self, current, elapsed_sec):
        # elapsed = (datetime.datetime.now() - self.started).seconds
        pct = self.pct(current)
        if pct > 0:
            eta = elapsed_sec / self.pct(current)
        else:
            return None

        remaining = eta - elapsed_sec
        return remaining

    def pretty_time(self, secs):
        if secs is None:
            return ""

        if secs > 60:
            mins, secs = divmod(secs, 60)
            if mins > 60:
                hours, mins = divmod(mins, 60)
            else:
                hours = 0
        else:
            mins = 0
            hours = 0

        if hours:
            s = "%d:%02d:%02d" % (hours, mins, secs)
        elif mins:
            s = "%d:%02d" % (mins, secs)
        else:
            s = "0:%02d" % secs

        return s

    def done(self, overwrite=True):
        if overwrite:
            sys.stderr.write('\r')
            sys.stderr.write(' ' * self.last_len)
            sys.stderr.write('\b' * self.last_len)

        elapsed = (datetime.datetime.now() - self.started).seconds
        sys.stderr.write("Done! (%s)\n" % self.pretty_time(elapsed))
        sys.stderr.flush()

    def print_status(self, current=None, extra='', overwrite=True):
        self.i += 1
        if self.modulo and self.i % self.modulo > 0:
            return

        now = datetime.datetime.now()

        if self._last_update:
            elapsed = (now - self._last_update)
            millis = (elapsed.seconds * 1000) + (elapsed.microseconds / 1000)
            if millis < self.min_ms_between_updates:
                return

        self._last_update = now

        if not self._started:
            self._started = now
            elapsed_sec = 0
        else:
            td = now - self.started
            elapsed_sec = (td.days * 86400) + td.seconds

        if current is None:
            if self.fileobj:
                current = self.fileobj.tell()
            else:
                current = self.last_step + self.step

        self.last_step = current

        if overwrite:
            sys.stderr.write("\r")
            if self.last_len:
                sys.stderr.write(' ' * self.last_len)
            sys.stderr.write("\r")

        if extra:
            extra = " | %s" % extra

        if self.prog_bar_length > 0:
            pct_current = self.pct(current)
            completed = int(self.prog_bar_length * pct_current)
            remaining = self.prog_bar_length - completed
            prog_bar = '[%s>%s] ' % ('=' * completed, ' ' * (remaining - 1))
        else:
            prog_bar = ''

        line = "%6.1f%% %s %s %sETA: %s%s" % (pct_current * 100,
                                         self.spinner[self.spinner_pos],
                                         self.pretty_time(elapsed_sec),
                                         prog_bar,
                                         self.pretty_time(self.ave_remaining(current, elapsed_sec)),
                                         extra)
        width, height = getTerminalSize()
        if len(line) > width:
            line = line[:width]+Fore.RESET
        sys.stderr.write(line)

        if not overwrite:
            sys.stderr.write('\n')
        else:
            self.last_len = len(line)

        self.spinner_pos += 1
        if self.spinner_pos > 3:
            self.spinner_pos = 0
        sys.stderr.flush()

#
# code from https://gist.github.com/jtriley/1108174#file-terminalsize-py

def getTerminalSize():
    """ getTerminalSize()
     - get width and height of console
     - works on linux,os x,windows,cygwin(windows)
     originally retrieved from:
     http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
    """
    current_os = platform.system()
    tuple_xy = None
    if current_os == 'Windows':
        tuple_xy = _get_terminal_size_windows()
        if tuple_xy is None:
            tuple_xy = _get_terminal_size_tput()
            # needed for window's python in cygwin's xterm!
    if current_os in ['Linux', 'Darwin'] or current_os.startswith('CYGWIN'):
        tuple_xy = _get_terminal_size_linux()
    if tuple_xy is None:
        tuple_xy = (80, 25)      # default value
    return tuple_xy
 
 
def _get_terminal_size_windows():
    try:
        from ctypes import windll, create_string_buffer
        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            (bufx, bufy, curx, cury, wattr,
             left, top, right, bottom,
             maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
            return sizex, sizey
    except:
        pass
 

def _get_terminal_size_tput():
    # get terminal width
    # src: http://stackoverflow.com/questions/263890/how-do-i-find-the-width-height-of-a-terminal-window
    try:
        cols = int(subprocess.check_call(shlex.split('tput cols')))
        rows = int(subprocess.check_call(shlex.split('tput lines')))
        return (cols, rows)
    except:
        pass
 
 
def _get_terminal_size_linux():
    def ioctl_GWINSZ(fd):
        try:
            import fcntl
            import termios
            cr = struct.unpack('hh',
                               fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
            return cr
        except:
            pass
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        except:
            return None
    return int(cr[1]), int(cr[0])



if 'HIDE_ETA' in os.environ:
    ETA = _NoopETA
elif not sys.stderr.isatty() and 'SHOW_ETA' not in os.environ:
    ETA = _NoopETA
else:
    ETA = _ETA

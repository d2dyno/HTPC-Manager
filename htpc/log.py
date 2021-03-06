#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging
"""
import os
import cherrypy
import htpc
import logging
import logging.handlers
import sys
from settings import Setting
from cherrypy.lib.auth2 import require, member_of
import colorama


class Log:
    """ Root class """
    def __init__(self):
        """ Initialize the logger """
        self.logfile = os.path.join(htpc.DATADIR, 'htpcmanager.log')
        htpc.LOGGER = logging.getLogger()

        self.blacklistwords = BlackListFilter()

        # Disable colored stdout byt --nocolor
        if htpc.NOCOLOR:
            self.logch = logging.StreamHandler()
        else:
            self.logch = ColorizingStreamHandler(sys.stdout)

        self.logfh = logging.handlers.RotatingFileHandler(self.logfile, maxBytes=25000000, backupCount=2)

        logformatter = logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s', "%Y-%m-%d %H:%M:%S")
        self.logch.setFormatter(logformatter)
        self.logfh.setFormatter(logformatter)

        if htpc.LOGLEVEL == 'debug' or htpc.DEBUG:
            loglevel = logging.DEBUG
        elif htpc.LOGLEVEL == 'info':
            loglevel = logging.INFO
        elif htpc.LOGLEVEL == 'warning':
            loglevel = logging.WARNING
        elif htpc.LOGLEVEL == 'error':
            loglevel = logging.ERROR
        else:
            loglevel = logging.CRITICAL

        self.logch.setLevel(loglevel)
        self.logfh.setLevel(loglevel)
        htpc.LOGGER.setLevel(loglevel)

        self.logch.addFilter(self.blacklistwords)
        self.logfh.addFilter(self.blacklistwords)

        # Disable cherrypy access log
        logging.getLogger('cherrypy.access').propagate = False

        # Disable urllib3 logger, except from criticals
        logging.getLogger("requests").setLevel(logging.CRITICAL)

        # Only show errors for paramiko
        logging.getLogger("paramiko").setLevel(logging.CRITICAL)

        # apscheduler
        # logging.getLogger("apscheduler.scheduler").setLevel(logging.CRITICAL)

        htpc.LOGGER.addHandler(self.logch)
        htpc.LOGGER.addHandler(self.logfh)

        htpc.LOGGER.info("Welcome to HTPC Manager!")
        htpc.LOGGER.info("Loglevel set to " + htpc.LOGLEVEL)

    @cherrypy.expose()
    @require()
    def index(self):
        """ Show log """
        return htpc.LOOKUP.get_template('log.html').render(scriptname='log')

    @cherrypy.expose()
    @require()
    @cherrypy.tools.json_out()
    def getlog(self, lines=10, level=2):
        """ Get log as JSON """
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'][-int(level):]
        content = []
        try:
            for line in reversed(open(self.logfile, 'r').readlines()):
                line = line.split(' :: ')
                if len(line) > 1 and line[2] in levels:
                    content.append(line)
                    if len(content) >= int(lines):
                        break
        except IOError:
            # Can't log this error since there is no log file.
            pass

        return content

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    @require(member_of('admin'))
    def deletelog(self):
        try:
            open(self.logfile, 'w').close()
            return "Log file deleted"
        except Exception, e:
            return "Cannot delete log file: " + str(e)


class BlackListFilter(logging.Filter):
    def __init__(self):
        pass

    def filter(self, record):
        if htpc.DEBUG:
            return True
        else:
            fl = Setting.select().orderBy(Setting.q.key)
            bl = []
            for i in fl:
                if i.key.endswith("_apikey") or i.key.endswith("_username") or i.key.endswith("_password") or i.key.endswith("_passkey"):
                    if len(i.val) > 1:
                        bl.append(i.val)

            for item in bl:
                try:
                    if item in record.msg or item in "".join(record.args):
                        # hack to make logging happy
                        ras = ", ".join(record.args)
                        record.args = ras.replace(item, len(item) * '*')
                        record.msg = record.msg.replace(item, len(item) * '*')
                except:
                    pass
            return True


class ColorizingStreamHandler(logging.StreamHandler):
    color_map = {
        logging.DEBUG: colorama.Fore.CYAN,
        logging.WARNING: colorama.Fore.YELLOW,
        logging.ERROR: colorama.Fore.RED,
        logging.CRITICAL: colorama.Back.RED,
    }

    def __init__(self, stream, color_map=None):
        logging.StreamHandler.__init__(self, colorama.AnsiToWin32(stream).stream)
        if color_map is not None:
            self.color_map = color_map

    @property
    def is_tty(self):
        isatty = getattr(self.stream, 'isatty', None)
        return isatty and isatty()

    def format(self, record):
        message = logging.StreamHandler.format(self, record)
        if self.is_tty:
            # Don't colorize a traceback
            parts = message.split('\n', 1)
            parts[0] = self.colorize(parts[0], record)
            message = '\n'.join(parts)
        return message

    def colorize(self, message, record):
        try:
            return (self.color_map[record.levelno] + message +
                    colorama.Style.RESET_ALL)
        except KeyError:
            return message

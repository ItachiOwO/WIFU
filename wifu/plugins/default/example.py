#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import logging
import subprocess

import wifu
from wifu.plugins import Plugin


class Example(Plugin):
    __author__ = 'evilsocket@gmail.com'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'An example plugin for WiFU.'

    def __init__(self):
        logging.debug("example plugin created")
        self.running = False

    def on_loaded(self):
        logging.debug("example plugin loaded")

    def on_ready(self, agent):
        while True:
            if self.running:
                logging.info("example plugin is running")
                time.sleep(1)
            else:
                break

    def on_internet_available(self, agent):
        logging.debug("example plugin detected internet")

    def on_disconnected(self, agent):
        logging.debug("example plugin detected disconnect")

    def on_ai_best_reward(self, agent, reward):
        logging.debug("example plugin detected best reward: %d" % reward)

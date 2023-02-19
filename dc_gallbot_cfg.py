# -*- coding: utf-8 -*-
"""
Created on Sun Feb 19 17:29:40 2023

@author: NitroLab
"""

import yaml
from requests import get
from pathlib import PurePath

class GallbotConfig():
    def __init__(self, file_config):
        self.get_config(file_config)
    
    def get_config(self, file_config):
        with open(file_config, 'r', encoding="utf-8") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        self.repeat = config['repeat']
        self.use_cache  = config['use_cache']
        
        self.board_id = config['board_id']
        self.board_name = config['board_name']
        self.board_minor = config['board_minor']
        
        self.nick = config['nick']
        self.author = self.get_author(self.nick)
        self.password = config['password']

        self.doc_write = config['doc_write']
        self.doc_title = config['doc_title']
        self.doc_contents_file = config['doc_contents']

        self.doc_watch = config['doc_watch']
        self.doc_watch_keywords = config['doc_watch_keywords']

        self.comment_write = config['comment_write']
        self.comment_contents_file = config['comment_contents']

        p = PurePath(file_config)
        f = open(p.parent / self.doc_contents_file, encoding="utf-8")
        self.doc_contents = f.read()
        f = open(p.parent / self.comment_contents_file, encoding="utf-8")
        self.comment_contents = f.read()
        f.close()
        
        self.mirror = config['mirror']
        self.mirror_target_board_id = config['mirror_target_board_id']
        self.mirror_target_board_minor = config['mirror_target_board_minor']

        return
    
    def get_author(self, nick):
        ip = get('https://api.my-ip.io/ip').text
        ip_head = '.'.join(ip.split('.')[0:2])
        author = nick+"("+ip_head+")"
        return author
    
if __name__ == "__main__":
    config = GallbotConfig("conf/default.yaml")
    doc = config.doc_contents
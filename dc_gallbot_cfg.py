# -*- coding: utf-8 -*-
"""
Created on Sun Feb 19 17:29:40 2023

@author: NitroLab
"""

import yaml
from ipaddress import IPv4Address, ip_address
from requests import RequestException, get
from pathlib import PurePath

PUBLIC_IP_URLS = [
    "https://api.ip.pe.kr/json/",
    "https://api.my-ip.io/ip",
    "https://api.myip.com",
    "https://api.ipify.org",
]


def parse_public_ip_response(response):
    text = response.text.strip()
    content_type = response.headers.get("content-type", "")
    if "json" in content_type or text.startswith("{"):
        data = response.json()
        if isinstance(data, dict) and data.get("ip"):
            return str(data["ip"]).strip()
    return text


def validate_public_ip(value):
    parsed = ip_address(value)
    if not isinstance(parsed, IPv4Address):
        raise ValueError("Expected an IPv4 address, got {}".format(value))
    return str(parsed)


def get_public_ip(urls=PUBLIC_IP_URLS, timeout=3):
    errors = []
    for url in urls:
        try:
            response = get(url, timeout=timeout)
            response.raise_for_status()
            ip = validate_public_ip(parse_public_ip_response(response))
            if ip:
                return ip
        except (RequestException, ValueError, KeyError) as exc:
            errors.append("{}: {}".format(url, exc))
    raise RuntimeError("Could not get public IP from configured providers: {}".format("; ".join(errors)))


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
        self.mirror_cache_file = config.get('mirror_cache_file', 'caches/mirror_cache.sqlite')
        self.mirror_cleanup = config.get('mirror_cleanup', False)
        self.mirror_cleanup_delete = config.get('mirror_cleanup_delete', False)
        self.mirror_cleanup_recent = config.get('mirror_cleanup_recent', 10)
        self.mirror_cleanup_missing_cycles = config.get('mirror_cleanup_missing_cycles', 2)
        self.mirror_cleanup_scan_pages = config.get('mirror_cleanup_scan_pages', 3)

        return
    
    def get_author(self, nick):
        ip = get_public_ip()
        ip_head = '.'.join(ip.split('.')[0:2])
        author = nick+"("+ip_head+")"
        return author
    
if __name__ == "__main__":
    config = GallbotConfig("conf/default.yaml")
    doc = config.doc_contents

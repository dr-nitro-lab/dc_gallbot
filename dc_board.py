# -*- coding: utf-8 -*-
"""
Created on Fri Feb 17 15:06:31 2023

@author: NitroLab
"""

import pandas as pd
import re


PARTIAL_IP_RE = re.compile(r'^\d{1,3}\.\d{1,3}$')


def split_author_display(author, author_id=None):
    display = "" if author is None else str(author)
    normalized_author_id = "" if author_id is None else str(author_id)
    if normalized_author_id:
        return display, "", normalized_author_id

    last_open = display.rfind("(")
    last_close = display.rfind(")")
    if last_open >= 0 and last_close == len(display) - 1:
        suffix = display[last_open + 1:last_close]
        if PARTIAL_IP_RE.match(suffix):
            return display[:last_open], suffix, ""
    return display, "", ""


class Board():
    def __init__(self, board_id):
        self.cols = [
            'id', 'author', 'author_name', 'author_ip', 'author_id',
            'time', 'title', 'comment_count', 'contents',
        ]
        self.board_id = board_id
        self.df_board = pd.DataFrame([], columns=self.cols)
    
    def get_board(self):
        return self.df_board
    
    def set_board(self, df_board):
        self.df_board = df_board
    
    def to_csv(self, filename):
        self.df_board.to_csv(filename, index=False)
        
    def read_csv(self, filename):
        self.df_board = pd.read_csv(filename)
    
    def findAuthor(self, author):
        return self.df_board[self.df_board['author'] == author]
    def findContents(self, word):
        return self.df_board[self.df_board['contents']
                             .str.contains('|'.join(word))]
    def findTitle(self, word):
        return self.df_board[self.df_board['title']
                             .str.contains('|'.join(word))]
    def findContentsNTitle(self, word):
        contents = self.findContents(word)
        titles   = self.findTitle(word)
        return pd.concat([contents, titles]).drop_duplicates()\
                 .reset_index(drop=True)
    
    def warningSpam(self):
        consecutive=0
        last_author=None
        is_spam=pd.Series([False for _ in range(self.df_board.shape[0])])
        # self.df_board['is_spam']=False
        for i, author in reversed(list(enumerate(self.df_board['author'].tolist()))):
            if last_author==author:
                consecutive+=1
            if consecutive==3:
                # self.df_board.loc[i,'is_spam']=True
                # print(self.df_board['is_spam'])
                is_spam[i]=True
                # print(is_spam)
                consecutive=0
            last_author=author
        return is_spam

    def deleteCode(self):
        for i, text in enumerate(self.df_board['contents'].to_list()):
            ln_start, ln_end=-1,-1
            pstack=[]
            pdict={'(':')','[':']','{':'}'}
            p_open,p_close=pdict.keys(),pdict.values()
            lines=text.split('\n')
            for j,line in enumerate(lines):
                for k,c in enumerate(line):
                    if c in p_open:
                        pstack.append(pdict[c])
                    elif len(pstack)>0 and c == pstack[-1]:
                        pstack.pop()
                        if len(pstack)==0 and line[k+1]==';':
                            ln_end=j
            print("#################################################################################################")
            print(lines[:ln_end])
            print('-------------------------------------------------------------------------------------------------')
            print(lines[ln_end+1:])
            
            self.df_board['contents'][i]="\n".join(lines[ln_end+1:])
            
    def sepIP(self):
        authors = self.df_board['author'].to_list()
        if 'author_id' in self.df_board:
            author_ids = self.df_board['author_id'].to_list()
        else:
            author_ids = [None for _ in authors]
        names = []
        ips = []
        ids = []
        for author, author_id in zip(authors, author_ids):
            name, ip, parsed_id = split_author_display(author, author_id)
            names.append(name)
            ips.append(ip)
            ids.append(parsed_id)
        self.df_board['author_name'] = pd.Series(names)
        self.df_board['author_ip'] = pd.Series(ips)
        self.df_board['author_id'] = pd.Series(ids)
        self.df_board['nick'] = pd.Series(names)
        self.df_board['ip'] = pd.Series(ips)

# -*- coding: utf-8 -*-
"""
Created on Fri Feb 17 15:06:31 2023

@author: NitroLab
"""

import pandas as pd
import re

class Board():
    def __init__(self, board_id):
        self.cols = ['id', 'author', 'time', 'title', 'comment_count', 'contents']
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
        ip_pattern = r'^\d{1,3}\.\d{1,3}$'
        nick=self.df_board['author'].to_list()
        ip=pd.Series([None for _ in range(len(nick))])
        for i, author in enumerate(nick):
            last_open = author.rfind("(")
            last_close = author.rfind(")")
            if last_open==-1 or last_close==-1: # author에 괄호가 없으면 넘어감.
                continue
            if re.match(ip_pattern,author[last_open+1:last_close]): # ip 패턴 매칭되면 ip만 떼서 nick에 저장
                nick[i]=author[:last_open]
                ip[i]=author[last_open+1:last_close]
        self.df_board['nick']=pd.Series(nick)
        self.df_board['ip']=ip
        
    
if __name__ == "__main__":
    board = Board('jazz')
    # print(board.get_board())
    board.read_csv('test/jazz.csv')
    # print(board.get_board())

    # # 도배 (5연속 동일 작성자) 검출
    # print(board.warningSpam())
    # print(board.get_board())

    # # IP 분리
    # print(board.get_board()['author'])
    # board.sepIP()
    # print(board.get_board()[['author','nick','ip']])

    # 코드 제거
    for content in board.get_board()['contents'].to_list():
        print(content)
        print('####################################################')
    board.deleteCode()
    for content in board.get_board()['contents'].to_list():
        print(content)
        print('####################################################')

    # df_board = board.get_board()
    # print(df_board)
    # board.set_board(df_board)
    # print(board.get_board())
    # print(board.findAuthor("즉흥갤(124.63)"))
    # print(board.findContents(['자렛', '재즈', '몽고메리']))
    # print(board.findTitle(['자렛', '재즈', '몽고메리']))
    # print(board.findContentsNTitle(['자렛', '재즈', '몽고메리']))  
    # doc_contents = board.df_board.iloc[0].contents
    # print(doc_contents)
    # for idx, row in df_board.iterrows():
    #     print(row)
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 17 15:06:31 2023

@author: NitroLab
"""

import pandas as pd

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
    
if __name__ == "__main__":
    board = Board('jazz')
    print(board.get_board())
    board.read_csv('test/jazz.csv')
    print(board.get_board())
    df_board = board.get_board()
    print(df_board)
    board.set_board(df_board)
    print(board.get_board())
    print(board.findAuthor("즉흥갤(124.63)"))
    print(board.findContents(['자렛', '재즈', '몽고메리']))
    print(board.findTitle(['자렛', '재즈', '몽고메리']))
    print(board.findContentsNTitle(['자렛', '재즈', '몽고메리']))  
    doc_contents = board.df_board.iloc[0].contents
    print(doc_contents)
    for idx, row in df_board.iterrows():
        print(row)
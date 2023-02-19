# -*- coding: utf-8 -*-
"""
Created on Sat Feb 18 19:47:49 2023

@author: NitroLab
"""

import pandas as pd

class Comments():
    def __init__(self, board_id="", doc_id=0):
        self.cols = ['id', 'author', 'time', 'contents', 'is_reply']
        self.board_id = board_id
        self.doc_id = doc_id
        self.df_comments = pd.DataFrame([], columns=self.cols)
    
    def get_comments(self):
        return self.df_comments
    
    def set_comments(self, df_comments):
        self.df_comments = df_comments
    
    def to_csv(self, filename):
        self.df_comments.to_csv(filename, index=False)
        
    def read_csv(self, filename):
        self.df_comments = pd.read_csv(filename)
    
    def findAuthor(self, author):
        return self.df_comments[self.df_comments['author'] == author]
    def findContents(self, contents):
        return self.df_comments[self.df_comments['contents']
                             .str.contains('|'.join(contents))]
    
    def isAuthorExists(self, author):
        if(len(self.findAuthor(author)) == 0):
            return False
        return True
            
    
if __name__ == "__main__":
    comments = Comments('jazz', 80051)
    print(comments.get_comments())
    comments.read_csv('test/jazz.80051.comments.csv')
    print(comments.get_comments())
    df_comments = comments.get_comments()
    print(df_comments)
    comments.set_comments(df_comments)
    print(comments.get_comments())
    print(comments.findAuthor("ㅇㅇ(121.167)")['author'])
    print(comments.findContents(['쇼팽', '말러', '재즈'])['contents'])

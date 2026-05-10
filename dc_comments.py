# -*- coding: utf-8 -*-
"""
Created on Sat Feb 18 19:47:49 2023

@author: NitroLab
"""

import pandas as pd

class Comments():
    def __init__(self, board_id="", doc_id=0):
        self.cols = [
            'id', 'author', 'author_name', 'author_ip', 'author_id',
            'time', 'contents', 'is_reply',
        ]
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

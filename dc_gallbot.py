# -*- coding: utf-8 -*-
"""
Created on Wed Jan 26 03:53:10 2022

@author: NitroLab
"""

from requests import get
import dc_api
import asyncio
import pandas as pd
from dc_gallbot_cfg import GallbotConfig
from dc_board import Board
from dc_comments import Comments
from time import strftime

class Gallbot():
    """
    https://gall.dcinside.com/mgallery/board/view/?id=improvisation&no=1084

    1. [x] 주기적으로 지정된 게시판 읽기
        1. [x] 글 목록은 모바일 기준 1페이지 이내로 읽기 권고.
        2. [x] 읽기 후 가장 최근 작성된 글 번호 저장
    2. [x] 지정된 갤러리에 모바일 기준 1페이지 이내 (8개)에 봇글이 없는 경우, 지정된 글 게시
        1. [x] 봇글 존재 여부는 지정된 작성자 존재 여부로 파악한다.
        * (봇 전용 닉 지정 권고)
        2. [x] 봇글의 타이틀과 작성자, 게시 내용, 비밀번호는 저장된 설정 파일을 이용.
        3. [x] 봇글이 없는 경우 봇글 게시.
    3. [x] 지정된 갤러리에 지정된 키워드가 포함된 글이 올라올 시 지정된 댓글을 남김
        * 예: 포락갤에 문자열 '재즈'가 포함된 글이 게시될 경우 봇이 즉흥갤 링크 댓글 작성
        1. [x] 해당 글에 봇 전용 닉의 댓글 존재 여부 확인 후, 댓글이 없는 경우 즉시 댓글 작성.
        2. [x] 댓글의 작성자, 게시 내용, 비밀번호는 저장된 설정 파일을 이용.
        3. [x] 봇의 게시글은 제외
    4. [ ] 지정된 갤러리에 지정된 키워드가 올라오면 지정된 갤러리에 원글 출처와 함께 미러링
        * 예: 포락갤에 문자열 '재즈'가 포함된 글이 게시될 경우, 봇이 즉흥갤에 해당글을 포락갤 링크와 함께 게시
        1. [ ] 봇글의 작성자, 게시 내용은 원글을 따름
        2. [x] 봇글의 타이틀 앞에 출처 기록
        * 예: (재즈갤|80090) 재즈피아노 입문자, 마이너 스케일 관련 질문
        3. [x] 비밀번호는 저장된 설정 파일을 이용
        4. [x] 읽기 후 가장 최근 작성된 글 번호 저장
        5. [ ] https://github.com/dr-nitro-lab/dc_gallbot/issues/1 원문 추출 시 기본으로 생성되는 코드 제거
        6. [ ] 봇의 게시글은 제외
    
    """
    def __init__(self, file_config):
        self.get_config(file_config)

    async def run(self):
        while(True):
            # print(strftime('%Y.%m.%d %H:%M:%S'))
            try:
                await self.get_board()
            except:
                await asyncio.sleep(10)
                continue
            
            if(self.doc_write):
                print("({}) writing doc ... ".format(self.board_id), end="")
                if(len(self.board.findAuthor(self.author)) == 0):
                    await self.write_document()
                    print("done")
                else:
                    print("wait!")
            
            if(self.doc_watch):
                get_contents=True
                failed=False
                last_id = self.board.df_board["id"].iloc[0]
                try:
                    await self.get_board(self.board_id, get_contents, self.doc_watch_last_id)
                except:
                    await asyncio.sleep(10)
                    continue
                df_watch = self.board.findContentsNTitle(self.doc_watch_keywords)
                # print(df_watch)
                print("({}) watching keywords ... ".format(self.board_id))
                for idx, row in df_watch.iterrows():
                    if(row.id <= self.doc_watch_last_id):
                        break
                    if(self.comment_write):
                        print("({}) ({}) comment ... "\
                              .format(self.board_id, row.id), end="")
                        if(row.author == self.author):
                            print("(gallbot-generated doc)")
                        else:
                            await self.get_comments(self.board_id, row.id)
                            if(self.comments.isAuthorExists(self.author)):
                                print("already done")
                            else:
                                try:
                                    await self.write_comment(row.id)
                                except:
                                    print("failed")
                                    self.comment_write=False
                                    failed=True
                                print("done")
                    if(self.mirror):
                        print("({}) ({}) -> ({}) mirror ... "\
                              .format(self.board_id, row.id,
                                      self.mirror_target_board_id), end="")

                        if(row.author == self.author):
                            print("(gallbot-generated doc)")
                        else:
                            """
                            TODO: mirroring
                            """
                            title = "[{}] {}"\
                                    .format(self.board_name, row.title)
                            url = "https://m.dcinside.com/board/{}/{}"\
                                  .format(self.board_id, row.id)
                            author = row.author
                            contents = "출처: " + url
                            print(title)
                            # print(url)
                            try:
                                await self.write_document(\
                                    self.mirror_target_board_id,
                                    self.mirror_target_board_minor,
                                    author, title, contents)
                            except:
                                print("failed")
                                failed=True
                        print("done")
                # if(not failed):
                #     self.doc_watch_last_id = last_id
                self.doc_watch_last_id = last_id
                print("({}) last watched doc id: {}".format(self.board_id,
                                                            self.doc_watch_last_id))
            
            if(self.repeat == False):
                break
            await asyncio.sleep(10)

    def get_config(self, file_config):
        self.cfg = GallbotConfig(file_config)

        self.repeat = self.cfg.repeat
        self.use_cache = self.cfg.use_cache

        self.board_id = self.cfg.board_id
        self.board_name = self.cfg.board_name
        self.board_minor = self.cfg.board_minor

        self.nick = self.cfg.nick
        self.author = self.cfg.author
        self.password = self.cfg.password
        
        self.board = Board(self.board_id)
        self.doc_write = self.cfg.doc_write
        self.doc_title = self.cfg.doc_title
        self.doc_contents = self.cfg.doc_contents

        self.doc_watch = self.cfg.doc_watch
        self.doc_watch_keywords = self.cfg.doc_watch_keywords
        self.doc_watch_last_id = 0

        self.comments = Comments()
        self.comment_write = self.cfg.comment_write
        self.comment_contents=self.cfg.comment_contents
        
        self.mirror = self.cfg.mirror
        self.mirror_target_board_id = self.cfg.mirror_target_board_id
        self.mirror_target_board_minor = self.cfg.mirror_target_board_minor
        return

    def get_author(self, nick):
        ip = get('https://api.my-ip.io/ip').text
        ip_head = '.'.join(ip.split('.')[0:2])
        author = nick+"("+ip_head+")"
        return author
    
    async def get_board(self, board_id=None, get_contents=False, last_id=0):
        board_id = self.board_id if board_id is None else board_id
        print("({}) getting board data ... ".format(self.board_id), end="")
        cols = ['id', 'author', 'time', 'title', 'comment_count', 'contents']
        df = pd.DataFrame([], columns=cols)
        async with dc_api.API() as api:
            i_post = 0
            async for index in api.board(board_id=self.board_id):
                if(int(index.id) <= last_id):
                    break
                if(get_contents):
                    print("({}|{}) getting doc ... ".format(self.board_id, index.id), end="")
                    doc = await self.get_document(int(index.id))
                    contents = doc.contents
                    print("done")
                else:
                    contents = ""
                df_row = pd.DataFrame([[int(index.id), index.author, index.time,
                                       index.title, int(index.comment_count),
                                       contents]],
                                      columns=cols)
                df = pd.concat([df, df_row], ignore_index=True)
                i_post = i_post + 1
                if(i_post == 8):
                    if (self.use_cache):
                        df.to_csv('caches/' + self.board_id+".csv", index=False)
                    self.board.set_board(df)
                    print('done')
                    return df
        self.board.set_board(df)
        print('done')
        return df


    async def write_document(self,
                             board_id=None, board_minor=None,
                             name=None, title=None, contents=None):
        board_id    = self.board_id    if board_id    is None else board_id
        board_minor = self.board_minor if board_minor is None else board_minor
        name     = self.nick         if name     is None else name
        title    = self.doc_title    if title    is None else title
        contents = self.doc_contents if contents is None else contents
        
        async with dc_api.API() as api:
            doc_id = await api.write_document(
                               board_id=board_id,
                               name=name,
                               password=self.password, 
                               title=title,
                               contents=contents,
                               is_minor=board_minor)
        return doc_id

    async def get_document(self, doc_id):
        async with dc_api.API() as api:
            doc = await api.document(board_id=self.board_id, document_id=doc_id)
        return doc
    
    async def write_comment(self, doc_id,
                            name=None, contents=None):
        name     = self.nick             if name     is None else name
        contents = self.comment_contents if contents is None else contents

        async with dc_api.API() as api:
            com_id = await api.write_comment \
                               (board_id=self.board_id, document_id=doc_id, 
                                name=name, password=self.password,
                                contents=contents)
        return com_id
    
    async def get_comments(self, board_id=None, doc_id=-1):
        board_id    = self.board_id    if board_id    is None else board_id
        cols = ['id', 'author', 'time', 'contents', 'is_reply']
        df = pd.DataFrame([], columns=cols)
        if doc_id < 0:
            return df
        async with dc_api.API() as api:
            async for comm in api.comments(board_id=self.board_id, document_id=doc_id):
                df_row = pd.DataFrame([[int(comm.id), comm.author, comm.time,
                                       comm.contents, comm.is_reply]],
                                      columns=cols)
                df = pd.concat([df, df_row], ignore_index=True)
        if (self.use_cache):
            df.to_csv('caches/'+self.board_id+".comments.csv", index=False)
        self.comments.set_comments(df)
        return df

if __name__ == "__main__":
    gallbot = Gallbot("conf/default.yaml")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # 'RuntimeError: There is no current event loop...'
        loop = None
    
    if loop and loop.is_running():
        print('Async event loop already running. Adding coroutine to the event loop.')
        tsk = loop.create_task(gallbot.run())
        # ^-- https://docs.python.org/3/library/asyncio-task.html#task-object
        # Optionally, a callback function can be executed when the coroutine completes
        tsk.add_done_callback(
            lambda t: print(f'Task done with result={t.result()}  << return val of run()'))
        # loop.close()
    else:
        print('Starting new event loop')
        asyncio.run(gallbot.run())

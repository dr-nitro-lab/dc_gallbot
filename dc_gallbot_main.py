# -*- coding: utf-8 -*-
"""
Created on Sun Feb 19 22:40:24 2023

@author: NitroLab
"""

import asyncio
from dc_gallbot import Gallbot

async def run(self):
    pass

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
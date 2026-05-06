# -*- coding: utf-8 -*-
"""
Created on Sun Feb 19 22:40:24 2023

@author: NitroLab
"""

import argparse
import asyncio
from pathlib import Path
from dc_gallbot import Gallbot
import yaml

DEFAULT_CONFIG_LIST = "conf/gall_conf_list.yaml"
LOCAL_CONFIG_LIST = "conf/gall_conf_list.local.yaml"


def load_config_files(config_list_file=None):
    if config_list_file is None:
        local_path = Path(LOCAL_CONFIG_LIST)
        config_list_file = LOCAL_CONFIG_LIST if local_path.exists() else DEFAULT_CONFIG_LIST
    with open(config_list_file, 'r', encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config['gall_conf_list'], config_list_file


async def run_all(config_files, dry_run=False, once=False, interval_seconds=10, doc_write_only=False, doc_write_use_gallery_nickname=False, doc_write_html_memo=False, doc_write_backend="mobile", doc_write_pc_use_html=False):
    max_cycles = 1 if once else None
    list_gallbot = [Gallbot('conf/' + conf, dry_run=dry_run) for conf in config_files]
    if doc_write_only:
        for gallbot in list_gallbot:
            gallbot.doc_watch = False
            gallbot.comment_write = False
            gallbot.mirror = False
    if doc_write_use_gallery_nickname:
        for gallbot in list_gallbot:
            gallbot.doc_write_use_gallery_nickname = True
    if doc_write_html_memo:
        for gallbot in list_gallbot:
            gallbot.doc_write_html_memo = True
    for gallbot in list_gallbot:
        gallbot.doc_write_backend = doc_write_backend
        gallbot.doc_write_pc_use_html = doc_write_pc_use_html
    await asyncio.gather(*[
        gallbot.run(max_cycles=max_cycles, interval_seconds=interval_seconds)
        for gallbot in list_gallbot
    ])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run configured DCInside gallbots.")
    parser.add_argument("--dry-run", action="store_true", help="Read and decide only; do not write posts or comments.")
    parser.add_argument("--once", action="store_true", help="Run one polling cycle per configured gallbot.")
    parser.add_argument("--interval", type=float, default=10, help="Polling interval in seconds.")
    parser.add_argument("--config", action="append", help="Run only the named config file under conf/. Can be passed more than once.")
    parser.add_argument("--live-doc-write-only", action="store_true", help="Live mode safety switch: only doc_write is allowed; watchers, comments, and mirrors are disabled.")
    parser.add_argument("--doc-write-use-gallery-nickname", action="store_true", help="For doc_write, leave the custom nickname blank and let the gallery use its configured nonmember nickname.")
    parser.add_argument("--doc-write-html-memo", action="store_true", help="For doc_write, submit the configured contents as mobile-editor HTML.")
    parser.add_argument("--doc-write-backend", choices=("mobile", "pc"), default="mobile", help="Select the write endpoint family for doc_write.")
    parser.add_argument("--doc-write-pc-use-html", action="store_true", help="For PC doc_write, set the write form use_html field to Y.")
    parser.add_argument("--config-list", help="Config list yaml. Defaults to conf/gall_conf_list.local.yaml when it exists.")
    args = parser.parse_args()

    config_files, config_list_file = load_config_files(args.config_list)
    config_files = args.config if args.config else config_files
    print("Config list: {}".format(config_list_file))

    if args.live_doc_write_only and args.dry_run:
        print("Starting doc-write-only dry-run event loop")
    elif args.live_doc_write_only:
        print("Starting doc-write-only live event loop")
    elif args.dry_run:
        print("Starting dry-run event loop")
    else:
        print("Starting live event loop")

    if args.live_doc_write_only and not args.once:
        raise SystemExit("--live-doc-write-only requires --once")

    asyncio.run(run_all(
        config_files,
        dry_run=args.dry_run,
        once=args.once,
        interval_seconds=args.interval,
        doc_write_only=args.live_doc_write_only,
        doc_write_use_gallery_nickname=args.doc_write_use_gallery_nickname,
        doc_write_html_memo=args.doc_write_html_memo,
        doc_write_backend=args.doc_write_backend,
        doc_write_pc_use_html=args.doc_write_pc_use_html,
    ))

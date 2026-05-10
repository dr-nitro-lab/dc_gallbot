import argparse
import asyncio
from pathlib import Path
import sys

API_REPO_DIR = Path(__file__).resolve().parents[1] / "api_repo"
if API_REPO_DIR.is_dir():
    sys.path.insert(0, str(API_REPO_DIR))

import dc_api
from moderation_cache import ModerationCandidateCache


def parse_args():
    parser = argparse.ArgumentParser(
        description="Print local moderation candidates from sqlite."
    )
    parser.add_argument(
        "--cache-file",
        default="caches/moderation_candidates.sqlite",
        help="Local moderation candidate sqlite file.",
    )
    parser.add_argument("--board-id", help="Show only one gallery id.")
    parser.add_argument(
        "--status",
        action="append",
        default=None,
        help="Candidate status to show. Defaults to new. Can be passed more than once.",
    )
    parser.add_argument(
        "--all-statuses",
        action="store_true",
        help="Show all statuses instead of only new candidates.",
    )
    parser.add_argument("--target-type", choices=("article", "comment"))
    parser.add_argument("--rule-id")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--skip-visible-check",
        action="store_true",
        help="Do not read board lists to check whether source articles are visible.",
    )
    parser.add_argument(
        "--visible-scan",
        type=int,
        default=80,
        help="Number of recent board-list rows to read for visibility checks.",
    )
    return parser.parse_args()


async def visible_article_indexes(rows, num):
    boards = sorted({row["board_id"] for row in rows})
    visible_by_board = {}
    async with dc_api.API() as api:
        for board_id in boards:
            indexes = {}
            async for index in api.board(board_id=board_id, num=num):
                indexes[int(index.id)] = index
            visible_by_board[board_id] = indexes
    return visible_by_board


def visibility_label(row, visible_by_board):
    if visible_by_board is None:
        return "not-checked"
    indexes = visible_by_board.get(row["board_id"], {})
    if not indexes:
        return "unknown"
    article_id = int(row["article_id"])
    if article_id in indexes:
        return "visible"
    min_id = min(indexes)
    max_id = max(indexes)
    if article_id < min_id:
        return "older-than-scan({}..{})".format(min_id, max_id)
    return "missing-from-scan({}..{})".format(min_id, max_id)


def article_url(row):
    return "https://gall.dcinside.com/mgallery/board/view/?id={}&no={}".format(
        row["board_id"],
        row["article_id"],
    )


def compact(value, limit=180):
    value = " ".join(str(value or "").split())
    if len(value) <= limit:
        return value
    return value[:limit - 3] + "..."


def print_groups(groups):
    if not groups:
        print("No moderation candidates found.")
        return
    print("Candidate groups:")
    for group in groups:
        print(
            "- {board_id} {status} {target_type} {rule_id} "
            "({rule_type}): {count}".format(**group)
        )


def print_rows(rows, visible_by_board):
    if not rows:
        return
    print()
    print("Recent candidates:")
    for row in rows:
        target = "{}/{}".format(row["board_id"], row["article_id"])
        if row["target_type"] == "comment":
            target += "#comment-{}".format(row["comment_id"])
        print()
        print("#{} [{}] {} {}".format(row["id"], row["status"], row["target_type"], target))
        print("  rule: {} ({}) action={}".format(
            row["rule_id"],
            row["rule_type"],
            row["proposed_action"],
        ))
        if "auto_action" in row.keys():
            print("  auto: {} delete={} ip_block={} hour={}".format(
                bool(row["auto_action"]),
                bool(row["del_chk"]),
                bool(row["avoid_type_chk"]),
                row["avoid_hour"],
            ))
        if "matched_field" in row.keys() and row["matched_field"]:
            print("  field: {}".format(row["matched_field"]))
        print("  matched: {}".format(compact(row["matched_text"], limit=80)))
        print("  author: {}".format(compact(row["author"], limit=80)))
        author_parts = []
        if "author_name" in row.keys() and row["author_name"]:
            author_parts.append("name={}".format(compact(row["author_name"], limit=60)))
        if "author_ip" in row.keys() and row["author_ip"]:
            author_parts.append("ip={}".format(compact(row["author_ip"], limit=20)))
        if "author_id" in row.keys() and row["author_id"]:
            author_parts.append("id={}".format(compact(row["author_id"], limit=60)))
        if author_parts:
            print("  author_parts: {}".format(" ".join(author_parts)))
        if row["title"]:
            print("  title: {}".format(compact(row["title"], limit=120)))
        if row["excerpt"]:
            print("  excerpt: {}".format(compact(row["excerpt"])))
        print("  seen: count={} first={} last={}".format(
            row["seen_count"],
            row["first_seen_at"],
            row["last_seen_at"],
        ))
        print("  source: {}".format(visibility_label(row, visible_by_board)))
        print("  url: {}".format(article_url(row)))


async def main():
    args = parse_args()
    cache_path = Path(args.cache_file)
    if not cache_path.exists():
        print("Moderation candidate cache not found: {}".format(cache_path))
        return 0

    statuses = None if args.all_statuses else (args.status or ["new"])
    cache = ModerationCandidateCache(cache_path)
    groups = cache.candidate_groups(board_id=args.board_id, statuses=statuses)
    rows = cache.recent_candidates(
        board_id=args.board_id,
        statuses=statuses,
        target_type=args.target_type,
        rule_id=args.rule_id,
        limit=args.limit,
    )
    visible_by_board = None
    if rows and not args.skip_visible_check:
        visible_by_board = await visible_article_indexes(rows, args.visible_scan)
    print_groups(groups)
    print_rows(rows, visible_by_board)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

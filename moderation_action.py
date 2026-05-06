import argparse
import json
from pathlib import Path
import sys
from typing import Iterable
from urllib.parse import urlencode

import requests

from moderation_cache import ModerationCandidateCache


ENDPOINT = "https://gall.dcinside.com/ajax/minor_manager_board_ajax/update_avoid_list"

PC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

AJAX_HEADERS = {
    **PC_HEADERS,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://gall.dcinside.com",
}

MANAGER_MARKERS = [
    "minor_manager_checkbox-tmpl",
    "minor_manager_commment_del_btn-tmpl",
    "minor_manager_commment_buttons-tmpl",
    "minor_block_pop-tmpl",
    "del_comment_manager",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare or execute a reviewed moderation candidate action."
    )
    parser.add_argument("--candidate-id", type=int, required=True)
    parser.add_argument(
        "--cache-file",
        default="caches/moderation_candidates.sqlite",
        help="Local moderation candidate sqlite file.",
    )
    parser.add_argument(
        "--cookie-file",
        default="conf/dcinside_cookies.json",
        help="Local manager-session cookie JSON or Netscape cookies.txt.",
    )
    parser.add_argument("--galltype", default="M")
    parser.add_argument("--avoid-hour", default="1")
    parser.add_argument("--avoid-reason", default="0")
    parser.add_argument("--reason-text", default="운영 기준 위반")
    parser.add_argument("--delete", action="store_true", help="Set del_chk=1.")
    parser.add_argument("--ip-block", action="store_true", help="Set avoid_type_chk=1.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Submit the manager action. Default only prepares and audits dry-run.",
    )
    parser.add_argument(
        "--allow-gallery",
        action="append",
        default=[],
        help="Gallery id allowlist required for --execute.",
    )
    parser.add_argument(
        "--confirm-target",
        default="",
        help="Exact confirmation token required for --execute. Dry-run prints it.",
    )
    return parser.parse_args()


def load_cookie_rows(path):
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit("cookie file is empty: {}".format(path))
    if text.startswith("[") or text.startswith("{"):
        data = json.loads(text)
        if isinstance(data, dict):
            if "cookies" in data and isinstance(data["cookies"], list):
                data = data["cookies"]
            else:
                data = [
                    {"name": str(name), "value": str(value)}
                    for name, value in data.items()
                ]
        if not isinstance(data, list):
            raise SystemExit("JSON cookie file must be a list, {cookies: []}, or name/value object")
        return [dict(row) for row in data]

    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            continue
        domain, _flag, path_value, secure, _expires, name, value = parts
        rows.append({
            "domain": domain,
            "path": path_value,
            "secure": secure.upper() == "TRUE",
            "name": name,
            "value": value,
        })
    if not rows:
        raise SystemExit("No cookies found. Use JSON export or Netscape cookies.txt format.")
    return rows


def import_cookies(session, rows: Iterable[dict]):
    names = []
    for row in rows:
        name = str(row.get("name", ""))
        value = str(row.get("value", ""))
        if not name:
            continue
        session.cookies.set(
            name,
            value,
            domain=str(row.get("domain") or ".dcinside.com"),
            path=str(row.get("path") or "/"),
        )
        names.append(name)
    return sorted(set(names))


def redacted(value):
    if not value:
        return "(missing)"
    if len(value) <= 8:
        return "<redacted>"
    return "{}...{} ({} chars)".format(value[:4], value[-4:], len(value))


def article_url(candidate):
    return "https://gall.dcinside.com/mgallery/board/view/?id={}&no={}".format(
        candidate["board_id"],
        candidate["article_id"],
    )


def target_no(candidate):
    if candidate["target_type"] == "comment":
        return int(candidate["comment_id"])
    return int(candidate["article_id"])


def parent_no(candidate):
    if candidate["target_type"] == "comment":
        return int(candidate["article_id"])
    return ""


def confirmation_token(candidate, args):
    return ":".join([
        "candidate",
        str(candidate["id"]),
        candidate["board_id"],
        candidate["target_type"],
        str(target_no(candidate)),
        "delete={}".format(1 if args.delete else 0),
        "ip={}".format(1 if args.ip_block else 0),
        "hour={}".format(args.avoid_hour),
    ])


def manager_marker_probe(session, candidate):
    url = article_url(candidate)
    response = session.get(url, timeout=15)
    found = [marker for marker in MANAGER_MARKERS if marker in response.text]
    print("article GET: {} {}".format(response.status_code, response.url))
    print("manager page markers:", ", ".join(found) if found else "(none)")
    return response.url, found, response.status_code


def quick_conf_probe(session, referer, ci_t, candidate, galltype):
    headers = {**AJAX_HEADERS, "Referer": referer}
    response = session.post(
        "https://gall.dcinside.com/ajax/managements_ajax/get_quick_avoid_conf",
        headers=headers,
        data={
            "ci_t": ci_t,
            "gallery_id": candidate["board_id"],
            "_GALLTYPE_": galltype,
        },
        timeout=15,
    )
    print("quick avoid conf POST:", response.status_code)
    print("quick avoid conf response:", " ".join(response.text.split())[:500])


def prepare_payload(candidate, args, ci_t):
    return [
        ("ci_t", ci_t),
        ("id", candidate["board_id"]),
        ("nos[]", str(target_no(candidate))),
        ("parent", str(parent_no(candidate))),
        ("avoid_hour", str(args.avoid_hour)),
        ("avoid_reason", str(args.avoid_reason)),
        ("avoid_reason_txt", str(args.reason_text)),
        ("del_chk", "1" if args.delete else "0"),
        ("_GALLTYPE_", str(args.galltype)),
        ("avoid_type_chk", "1" if args.ip_block else "0"),
    ]


def redact_payload(payload):
    return [
        (name, redacted(value) if name == "ci_t" else value)
        for name, value in payload
    ]


def validate_execute(args, candidate, found_markers):
    expected = confirmation_token(candidate, args)
    if candidate["board_id"] not in args.allow_gallery:
        raise SystemExit("--execute requires --allow-gallery {}".format(candidate["board_id"]))
    if args.confirm_target != expected:
        raise SystemExit("--execute requires --confirm-target {!r}".format(expected))
    if candidate["status"] not in ("new", "review"):
        raise SystemExit("candidate status is {!r}; refusing to execute".format(candidate["status"]))
    if not found_markers:
        raise SystemExit("manager markers were not found; refusing to execute")


def submit_action(session, referer, payload):
    headers = {**AJAX_HEADERS, "Referer": referer}
    response = session.post(ENDPOINT, headers=headers, data=payload, timeout=15)
    return response.status_code, response.text


def response_result(response_text):
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return "non-json", ""
    return str(data.get("result", "")), str(data.get("msg", "") or data.get("message", ""))


def print_candidate(candidate):
    print("candidate #{} [{}] {} {}/{}".format(
        candidate["id"],
        candidate["status"],
        candidate["target_type"],
        candidate["board_id"],
        target_no(candidate),
    ))
    print("rule: {} ({}) action={}".format(
        candidate["rule_id"],
        candidate["rule_type"],
        candidate["proposed_action"],
    ))
    print("title:", candidate["title"])
    print("matched:", candidate["matched_text"])


def main():
    args = parse_args()
    cache = ModerationCandidateCache(args.cache_file)
    candidate = cache.get_candidate(args.candidate_id)
    if candidate is None:
        raise SystemExit("candidate not found: {}".format(args.candidate_id))

    cookie_path = Path(args.cookie_file)
    if not cookie_path.exists():
        raise SystemExit("cookie file not found: {}".format(cookie_path))

    session = requests.Session()
    session.headers.update(PC_HEADERS)
    names = import_cookies(session, load_cookie_rows(cookie_path))
    ci_t = session.cookies.get("ci_c", domain=".dcinside.com") or session.cookies.get("ci_c") or ""

    print_candidate(candidate)
    print("cookies imported:", len(names))
    print("interesting cookie names:", ", ".join(name for name in names if name in {"PHPSESSID", "ci_c"}) or "(none)")
    print("ci_t from ci_c cookie:", redacted(ci_t))
    if not ci_t:
        raise SystemExit("Cannot prepare manager payload because ci_c cookie was not found.")

    referer, found_markers, _article_status = manager_marker_probe(session, candidate)
    quick_conf_probe(session, referer, ci_t, candidate, args.galltype)
    payload = prepare_payload(candidate, args, ci_t)
    redacted_pairs = redact_payload(payload)
    expected = confirmation_token(candidate, args)

    print()
    print("mode:", "EXECUTE" if args.execute else "DRY RUN ONLY: not submitting update_avoid_list")
    print("endpoint:", ENDPOINT)
    print("referer:", referer)
    print("expected --confirm-target:", expected)
    print("payload:")
    for name, value in redacted_pairs:
        print("  {}={}".format(name, value))
    print("urlencoded payload with ci_t redacted:")
    print(urlencode(redacted_pairs))

    if not args.execute:
        cache.audit_candidate_action(
            candidate["id"],
            mode="dry-run",
            endpoint=ENDPOINT,
            target_no=target_no(candidate),
            parent_no=parent_no(candidate),
            avoid_hour=args.avoid_hour,
            avoid_reason=args.avoid_reason,
            reason_text=args.reason_text,
            del_chk=args.delete,
            avoid_type_chk=args.ip_block,
            status_code=None,
            result="prepared",
            message="",
            response_text="",
        )
        print("audit: dry-run recorded in", args.cache_file)
        return 0

    validate_execute(args, candidate, found_markers)
    status_code, response_text = submit_action(session, referer, payload)
    result, message = response_result(response_text)
    cache.audit_candidate_action(
        candidate["id"],
        mode="execute",
        endpoint=ENDPOINT,
        target_no=target_no(candidate),
        parent_no=parent_no(candidate),
        avoid_hour=args.avoid_hour,
        avoid_reason=args.avoid_reason,
        reason_text=args.reason_text,
        del_chk=args.delete,
        avoid_type_chk=args.ip_block,
        status_code=status_code,
        result=result,
        message=message,
        response_text=response_text,
    )
    print()
    print("submitted update_avoid_list")
    print("status:", status_code)
    print("result:", result)
    if message:
        print("message:", message)
    print("response:", " ".join(response_text.split())[:500])
    if status_code == 200 and result == "success":
        cache.mark_candidate_status(candidate["id"], "actioned")
        return 0
    cache.mark_candidate_status(candidate["id"], "action_failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

import sqlite3
from pathlib import Path


class ModerationCandidateCache:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS moderation_candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board_id TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    article_id INTEGER NOT NULL,
                    comment_id INTEGER NOT NULL DEFAULT 0,
                    author TEXT NOT NULL DEFAULT '',
                    author_name TEXT NOT NULL DEFAULT '',
                    author_ip TEXT NOT NULL DEFAULT '',
                    author_id TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    excerpt TEXT NOT NULL DEFAULT '',
                    rule_id TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    matched_text TEXT NOT NULL DEFAULT '',
                    proposed_action TEXT NOT NULL DEFAULT 'review',
                    status TEXT NOT NULL DEFAULT 'new',
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    seen_count INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(
                        board_id, target_type, article_id, comment_id,
                        rule_id, matched_text
                    )
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_moderation_candidates_recent
                ON moderation_candidates(board_id, status, last_seen_at DESC)
                """
            )
            self._ensure_column(conn, "matched_field", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "author_name", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "author_ip", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "author_id", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "auto_action", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "avoid_hour", "TEXT NOT NULL DEFAULT '1'")
            self._ensure_column(conn, "avoid_reason", "TEXT NOT NULL DEFAULT '0'")
            self._ensure_column(conn, "reason_text", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "del_chk", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "avoid_type_chk", "INTEGER NOT NULL DEFAULT 0")

    def _ensure_column(self, conn, name, definition):
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(moderation_candidates)").fetchall()
        }
        if name not in columns:
            conn.execute(
                "ALTER TABLE moderation_candidates ADD COLUMN {} {}".format(
                    name,
                    definition,
                )
            )

    def record_candidate(self, candidate):
        comment_id = int(candidate.get("comment_id") or 0)
        params = (
            candidate["board_id"],
            candidate["target_type"],
            int(candidate["article_id"]),
            comment_id,
            candidate.get("author") or "",
            candidate.get("author_name") or "",
            candidate.get("author_ip") or "",
            candidate.get("author_id") or "",
            candidate.get("title") or "",
            candidate.get("excerpt") or "",
            candidate["rule_id"],
            candidate["rule_type"],
            candidate.get("matched_field") or "",
            candidate.get("matched_text") or "",
            candidate.get("proposed_action") or "review",
            1 if candidate.get("auto_action") else 0,
            str(candidate.get("avoid_hour") or "1"),
            str(candidate.get("avoid_reason") or "0"),
            candidate.get("reason_text") or "",
            1 if candidate.get("delete") else 0,
            1 if candidate.get("ip_block") else 0,
        )
        with self._connect() as conn:
            exists = conn.execute(
                """
                SELECT id
                FROM moderation_candidates
                WHERE board_id = ?
                  AND target_type = ?
                  AND article_id = ?
                  AND comment_id = ?
                  AND rule_id = ?
                  AND matched_text = ?
                LIMIT 1
                """,
                (
                    candidate["board_id"],
                    candidate["target_type"],
                    int(candidate["article_id"]),
                    comment_id,
                    candidate["rule_id"],
                    candidate.get("matched_text") or "",
                ),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO moderation_candidates (
                    board_id, target_type, article_id, comment_id,
                    author, author_name, author_ip, author_id,
                    title, excerpt, rule_id, rule_type,
                    matched_field, matched_text, proposed_action,
                    auto_action, avoid_hour, avoid_reason, reason_text,
                    del_chk, avoid_type_chk
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(
                    board_id, target_type, article_id, comment_id,
                    rule_id, matched_text
                )
                DO UPDATE SET
                    author = excluded.author,
                    author_name = excluded.author_name,
                    author_ip = excluded.author_ip,
                    author_id = excluded.author_id,
                    title = excluded.title,
                    excerpt = excluded.excerpt,
                    matched_field = excluded.matched_field,
                    proposed_action = excluded.proposed_action,
                    auto_action = excluded.auto_action,
                    avoid_hour = excluded.avoid_hour,
                    avoid_reason = excluded.avoid_reason,
                    reason_text = excluded.reason_text,
                    del_chk = excluded.del_chk,
                    avoid_type_chk = excluded.avoid_type_chk,
                    last_seen_at = CURRENT_TIMESTAMP,
                    seen_count = seen_count + 1
                """,
                params,
            )
        return exists is None

    def record_candidates(self, candidates):
        created = 0
        updated = 0
        for candidate in candidates:
            if self.record_candidate(candidate):
                created += 1
            else:
                updated += 1
        return {"created": created, "updated": updated}

    def candidate_groups(self, board_id=None, statuses=None):
        where, params = self._candidate_filters(board_id=board_id, statuses=statuses)
        sql = """
            SELECT board_id, status, target_type, rule_id, rule_type, count(*) AS count
            FROM moderation_candidates
            {where}
            GROUP BY board_id, status, target_type, rule_id, rule_type
            ORDER BY board_id, status, target_type, rule_id
        """.format(where=where)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def pending_auto_candidates(self, board_id=None, limit=1):
        clauses = [
            "status = 'new'",
            "auto_action = 1",
            "proposed_action IN ('block', 'block_delete')",
        ]
        params = []
        if board_id:
            clauses.append("board_id = ?")
            params.append(board_id)
        params.append(int(limit))
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT *
                FROM moderation_candidates
                WHERE {where}
                ORDER BY first_seen_at ASC, id ASC
                LIMIT ?
                """.format(where=" AND ".join(clauses)),
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_candidates(self, board_id=None, statuses=None, target_type=None,
                          rule_id=None, limit=20):
        where, params = self._candidate_filters(
            board_id=board_id,
            statuses=statuses,
            target_type=target_type,
            rule_id=rule_id,
        )
        params.append(int(limit))
        sql = """
            SELECT *
            FROM moderation_candidates
            {where}
            ORDER BY last_seen_at DESC, id DESC
            LIMIT ?
        """.format(where=where)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get_candidate(self, candidate_id):
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT *
                FROM moderation_candidates
                WHERE id = ?
                """,
                (int(candidate_id),),
            ).fetchone()
        return dict(row) if row is not None else None

    def mark_candidate_status(self, candidate_id, status):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE moderation_candidates
                SET status = ?
                WHERE id = ?
                """,
                (status, int(candidate_id)),
            )

    def audit_candidate_action(self, candidate_id, *, mode, endpoint, target_no,
                               parent_no, avoid_hour, avoid_reason,
                               reason_text, del_chk, avoid_type_chk,
                               status_code, result, message, response_text):
        with self._connect() as conn:
            self._ensure_action_audit_table(conn)
            conn.execute(
                """
                INSERT INTO moderation_action_audit (
                    candidate_id, mode, endpoint, target_no, parent_no,
                    avoid_hour, avoid_reason, reason_text, del_chk,
                    avoid_type_chk, status_code, result, message, response_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(candidate_id),
                    mode,
                    endpoint,
                    str(target_no),
                    str(parent_no),
                    str(avoid_hour),
                    str(avoid_reason),
                    str(reason_text),
                    1 if del_chk else 0,
                    1 if avoid_type_chk else 0,
                    status_code,
                    result,
                    message,
                    response_text[:2000],
                ),
            )

    def action_count_since(self, mode, since_sql):
        with self._connect() as conn:
            self._ensure_action_audit_table(conn)
            row = conn.execute(
                """
                SELECT count(*)
                FROM moderation_action_audit
                WHERE mode = ?
                  AND result = 'success'
                  AND created_at >= {}
                """.format(since_sql),
                (mode,),
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def _ensure_action_audit_table(self, conn):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS moderation_action_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                candidate_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                target_no TEXT NOT NULL,
                parent_no TEXT NOT NULL,
                avoid_hour TEXT NOT NULL,
                avoid_reason TEXT NOT NULL,
                reason_text TEXT NOT NULL,
                del_chk INTEGER NOT NULL,
                avoid_type_chk INTEGER NOT NULL,
                status_code INTEGER,
                result TEXT NOT NULL,
                message TEXT NOT NULL,
                response_text TEXT NOT NULL
            )
            """
        )

    def _candidate_filters(self, board_id=None, statuses=None, target_type=None,
                           rule_id=None):
        clauses = []
        params = []
        if board_id:
            clauses.append("board_id = ?")
            params.append(board_id)
        if statuses:
            placeholders = ", ".join("?" for _ in statuses)
            clauses.append("status IN ({})".format(placeholders))
            params.extend(statuses)
        if target_type:
            clauses.append("target_type = ?")
            params.append(target_type)
        if rule_id:
            clauses.append("rule_id = ?")
            params.append(rule_id)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        return where, params

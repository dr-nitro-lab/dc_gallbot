import sqlite3
from pathlib import Path


class MirrorCache:
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
                CREATE TABLE IF NOT EXISTS mirror_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_board_id TEXT NOT NULL,
                    source_doc_id INTEGER NOT NULL,
                    source_title TEXT NOT NULL DEFAULT '',
                    target_board_id TEXT NOT NULL,
                    target_doc_id INTEGER NOT NULL,
                    target_title TEXT NOT NULL DEFAULT '',
                    target_is_minor INTEGER NOT NULL DEFAULT 0,
                    password TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TEXT,
                    missing_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    removed_at TEXT,
                    UNIQUE(source_board_id, source_doc_id, target_board_id)
                )
                """
            )
            self._ensure_column(conn, "target_last_seen_at", "TEXT")
            self._ensure_column(conn, "target_missing_count", "INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mirror_posts_cleanup
                ON mirror_posts(source_board_id, status, created_at DESC)
                """
            )

    def _ensure_column(self, conn, name, definition):
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(mirror_posts)").fetchall()
        }
        if name not in columns:
            conn.execute("ALTER TABLE mirror_posts ADD COLUMN {} {}".format(name, definition))

    def has_handled_source(self, source_board_id, source_doc_id, target_board_id):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM mirror_posts
                WHERE source_board_id = ?
                  AND source_doc_id = ?
                  AND target_board_id = ?
                  AND status IN ('active', 'removed', 'removed_external')
                LIMIT 1
                """,
                (source_board_id, int(source_doc_id), target_board_id),
            ).fetchone()
        return row is not None

    def record_mirror(self, source_board_id, source_doc_id, source_title,
                      target_board_id, target_doc_id, target_title,
                      target_is_minor, password):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO mirror_posts (
                    source_board_id, source_doc_id, source_title,
                    target_board_id, target_doc_id, target_title,
                    target_is_minor, password, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_board_id, source_doc_id, target_board_id)
                DO UPDATE SET
                    target_doc_id = excluded.target_doc_id,
                    target_title = excluded.target_title,
                    target_is_minor = excluded.target_is_minor,
                    password = excluded.password,
                    last_seen_at = CURRENT_TIMESTAMP,
                    target_last_seen_at = CURRENT_TIMESTAMP,
                    missing_count = 0,
                    target_missing_count = 0,
                    status = 'active',
                    removed_at = NULL
                """,
                (
                    source_board_id, int(source_doc_id), source_title or "",
                    target_board_id, int(target_doc_id), target_title or "",
                    1 if target_is_minor else 0, password or "",
                ),
            )

    def recent_active_by_source(self, source_board_id, limit):
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT *
                FROM mirror_posts
                WHERE source_board_id = ?
                  AND status = 'active'
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (source_board_id, int(limit)),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_seen(self, row_id):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE mirror_posts
                SET last_seen_at = CURRENT_TIMESTAMP,
                    missing_count = 0
                WHERE id = ?
                """,
                (int(row_id),),
            )

    def mark_target_seen(self, row_id):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE mirror_posts
                SET target_last_seen_at = CURRENT_TIMESTAMP,
                    target_missing_count = 0
                WHERE id = ?
                """,
                (int(row_id),),
            )

    def mark_missing(self, row_id):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE mirror_posts
                SET missing_count = missing_count + 1
                WHERE id = ?
                """,
                (int(row_id),),
            )
            row = conn.execute(
                "SELECT missing_count FROM mirror_posts WHERE id = ?",
                (int(row_id),),
            ).fetchone()
        return int(row[0])

    def mark_target_missing(self, row_id):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE mirror_posts
                SET target_missing_count = target_missing_count + 1
                WHERE id = ?
                """,
                (int(row_id),),
            )
            row = conn.execute(
                "SELECT target_missing_count FROM mirror_posts WHERE id = ?",
                (int(row_id),),
            ).fetchone()
        return int(row[0])

    def mark_removed(self, row_id):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE mirror_posts
                SET status = 'removed',
                    removed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (int(row_id),),
            )

    def mark_removed_external(self, row_id):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE mirror_posts
                SET status = 'removed_external',
                    removed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (int(row_id),),
            )

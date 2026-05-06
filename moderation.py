class ModerationMatcher:
    def __init__(self, rules):
        self.rules = [self._normalize_rule(rule, idx) for idx, rule in enumerate(rules or [])]

    def has_rules(self):
        return any(rule["values"] for rule in self.rules)

    def match_article(self, board_id, row):
        article_id = int(self._value(row, "id", 0))
        title = self._text(self._value(row, "title", ""))
        contents = self._text(self._value(row, "contents", ""))
        author = self._text(self._value(row, "author", ""))
        candidates = []
        for rule in self.rules:
            if not self._target_matches(rule, "article"):
                continue
            fields = {
                "author": author,
                "title": title,
                "contents": contents,
            }
            for matched_field, matched_text in self._rule_matches(rule, fields):
                candidates.append({
                    "board_id": board_id,
                    "target_type": "article",
                    "article_id": article_id,
                    "comment_id": 0,
                    "author": author,
                    "title": title,
                    "excerpt": self._excerpt_for_match(fields[matched_field], matched_text),
                    "rule_id": rule["id"],
                    "rule_type": rule["type"],
                    "matched_field": matched_field,
                    "matched_text": matched_text,
                    "proposed_action": rule["proposed_action"],
                    "auto_action": rule["auto_action"],
                    "avoid_hour": rule["avoid_hour"],
                    "avoid_reason": rule["avoid_reason"],
                    "reason_text": rule["reason_text"],
                    "delete": rule["delete"],
                    "ip_block": rule["ip_block"],
                })
        return candidates

    def match_comment(self, board_id, article_id, row, title=""):
        comment_id = int(self._value(row, "id", 0))
        contents = self._text(self._value(row, "contents", ""))
        author = self._text(self._value(row, "author", ""))
        candidates = []
        for rule in self.rules:
            if not self._target_matches(rule, "comment"):
                continue
            fields = {
                "author": author,
                "contents": contents,
            }
            for matched_field, matched_text in self._rule_matches(rule, fields):
                candidates.append({
                    "board_id": board_id,
                    "target_type": "comment",
                    "article_id": int(article_id),
                    "comment_id": comment_id,
                    "author": author,
                    "title": title or "",
                    "excerpt": self._excerpt_for_match(fields[matched_field], matched_text),
                    "rule_id": rule["id"],
                    "rule_type": rule["type"],
                    "matched_field": matched_field,
                    "matched_text": matched_text,
                    "proposed_action": rule["proposed_action"],
                    "auto_action": rule["auto_action"],
                    "avoid_hour": rule["avoid_hour"],
                    "avoid_reason": rule["avoid_reason"],
                    "reason_text": rule["reason_text"],
                    "delete": rule["delete"],
                    "ip_block": rule["ip_block"],
                })
        return candidates

    def _normalize_rule(self, rule, idx):
        rule = dict(rule or {})
        rule_type = rule.get("type", "keyword")
        default_fields = ["author"] if rule_type == "author" else ["title", "contents"]
        return {
            "id": str(rule.get("id") or "{}-{}".format(rule_type, idx + 1)),
            "type": rule_type,
            "values": [self._text(value) for value in rule.get("values", []) if self._text(value)],
            "target": rule.get("target", "both"),
            "fields": rule.get("fields", default_fields),
            "match": rule.get("match", "exact" if rule_type == "author" else "contains"),
            "case_sensitive": bool(rule.get("case_sensitive", rule_type == "author")),
            "proposed_action": rule.get("proposed_action", "review"),
            "auto_action": bool(rule.get("auto_action", False)),
            "avoid_hour": str(rule.get("avoid_hour", "1")),
            "avoid_reason": str(rule.get("avoid_reason", "0")),
            "reason_text": str(rule.get("reason_text", "운영 기준 위반")),
            "delete": bool(rule.get("delete", False)),
            "ip_block": bool(rule.get("ip_block", False)),
        }

    def _rule_matches(self, rule, fields):
        matches = []
        matched_values = set()
        for field_name in rule["fields"]:
            if field_name not in fields:
                continue
            field_value = fields[field_name]
            for expected in rule["values"]:
                if expected in matched_values:
                    continue
                if self._text_matches(field_value, expected, rule):
                    matches.append((field_name, expected))
                    matched_values.add(expected)
        return matches

    def _text_matches(self, actual, expected, rule):
        if not rule["case_sensitive"]:
            actual = actual.lower()
            expected = expected.lower()
        if rule["match"] == "exact":
            return actual == expected
        return expected in actual

    def _target_matches(self, rule, target):
        return rule["target"] in (target, "both")

    def _excerpt(self, value, limit=200):
        text = self._text(value).replace("\r\n", "\n").replace("\r", "\n")
        text = " ".join(text.split())
        if len(text) <= limit:
            return text
        return text[:limit - 3] + "..."

    def _excerpt_for_match(self, value, matched_text, limit=200):
        text = " ".join(self._text(value).replace("\r\n", "\n").replace("\r", "\n").split())
        needle = self._text(matched_text)
        if not needle or len(text) <= limit:
            return self._excerpt(text, limit=limit)
        index = text.lower().find(needle.lower())
        if index < 0:
            return self._excerpt(text, limit=limit)
        start = max(0, index - (limit // 2))
        end = min(len(text), start + limit)
        start = max(0, end - limit)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return prefix + text[start:end] + suffix

    def _value(self, row, name, default=None):
        if hasattr(row, name):
            return getattr(row, name)
        if isinstance(row, dict):
            return row.get(name, default)
        try:
            return row[name]
        except (KeyError, TypeError):
            return default

    def _text(self, value):
        if value is None:
            return ""
        return str(value)

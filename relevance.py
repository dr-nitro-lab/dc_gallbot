import re


class RelevanceScorer:
    def __init__(self, watch_keywords, positive_keywords=None, negative_keywords=None,
                 context_keywords=None, title_multiplier=2, contents_multiplier=1,
                 review_score=3, pass_score=7):
        self.positive = self._terms(positive_keywords, default_weight=1)
        if not self.positive:
            self.positive = self._terms(watch_keywords, default_weight=1)
        self.negative = self._terms(negative_keywords, default_weight=-3)
        self.context = self._terms(context_keywords, default_weight=1)
        self.title_multiplier = int(title_multiplier)
        self.contents_multiplier = int(contents_multiplier)
        self.review_score = int(review_score)
        self.pass_score = int(pass_score)

    def score(self, title, contents):
        title = title or ""
        contents = contents or ""
        title_score, title_hits = self._score_terms(title, self.positive, self.title_multiplier)
        contents_score, contents_hits = self._score_terms(contents, self.positive, self.contents_multiplier)
        context_score, context_hits = self._score_terms(title + "\n" + contents, self.context, 1)
        negative_score, negative_hits = self._score_terms(title + "\n" + contents, self.negative, 1)
        score = title_score + contents_score + context_score + negative_score
        if score >= self.pass_score:
            decision = "pass"
        elif score >= self.review_score:
            decision = "review"
        else:
            decision = "skip"
        return {
            "score": score,
            "decision": decision,
            "title_hits": title_hits,
            "contents_hits": contents_hits,
            "context_hits": context_hits,
            "negative_hits": negative_hits,
        }

    def _terms(self, value, default_weight):
        if not value:
            return []
        if isinstance(value, dict):
            items = value.items()
        else:
            items = [(term, default_weight) for term in value]
        terms = []
        for term, weight in items:
            term = str(term).strip()
            if not term:
                continue
            terms.append((term, int(weight)))
        return terms

    def _score_terms(self, text, terms, multiplier):
        if not text or not terms:
            return 0, []
        hits = []
        total = 0
        for term, weight in terms:
            count = len(re.findall(re.escape(term), text, re.IGNORECASE))
            if count <= 0:
                continue
            points = count * weight * multiplier
            total += points
            hits.append("{}:{}x{}={}".format(term, weight * multiplier, count, points))
        return total, hits

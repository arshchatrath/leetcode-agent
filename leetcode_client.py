"""LeetCode GraphQL + unofficial REST submit/poll client. Stdlib only."""
import html
import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass

GRAPHQL_URL = "https://leetcode.com/graphql"

# rotation name -> LeetCode GraphQL tag slug
TOPIC_SLUGS = {
    "arrays": "array",
    "strings": "string",
    "hashmaps": "hash-table",
    "two_pointers": "two-pointers",
    "dp": "dynamic-programming",
    "graphs": "graph",
    "trees": "tree",
}


@dataclass
class Question:
    question_id: str
    title: str
    title_slug: str
    content: str
    difficulty: str
    python3_stub: str
    topic_tags: list


def _auth_headers():
    session = os.environ["LEETCODE_SESSION"]
    csrf = os.environ["LEETCODE_CSRF_TOKEN"]
    return {
        "Cookie": f"LEETCODE_SESSION={session}; csrftoken={csrf}",
        "x-csrftoken": csrf,
    }


def _graphql(query: str, variables: dict | None = None) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "leetcode-auto-solver/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["data"]


def get_daily_challenge() -> str:
    query = """
    query questionOfToday {
      activeDailyCodingChallengeQuestion {
        date
        question { titleSlug }
      }
    }
    """
    data = _graphql(query)
    return data["activeDailyCodingChallengeQuestion"]["question"]["titleSlug"]


def _strip_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def get_question(title_slug: str) -> Question:
    query = """
    query questionData($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionId
        title
        titleSlug
        content
        difficulty
        exampleTestcases
        topicTags { name slug }
        codeSnippets { langSlug code }
      }
    }
    """
    q = _graphql(query, {"titleSlug": title_slug})["question"]
    python3_stub = next(
        (s["code"] for s in q["codeSnippets"] if s["langSlug"] == "python3"), ""
    )
    return Question(
        question_id=q["questionId"],
        title=q["title"],
        title_slug=q["titleSlug"],
        content=_strip_html(q["content"]),
        difficulty=q["difficulty"],
        python3_stub=python3_stub,
        topic_tags=[t["slug"] for t in q["topicTags"]],
    )


def list_problems_by_topic(topic_slug: str, exclude_slugs: set) -> list:
    # NOTE: this query is the part of LeetCode's unofficial API most likely to
    # have drifted. If it errors, open leetcode.com/problemset, check the
    # Network tab for the live request body, and update field/arg names.
    query = """
    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
      questionList: questionList(categorySlug: $categorySlug, limit: $limit, skip: $skip, filters: $filters) {
        total: totalNum
        questions: data { title titleSlug difficulty isPaidOnly topicTags { slug } }
      }
    }
    """
    variables = {"categorySlug": "", "skip": 0, "limit": 50, "filters": {"tags": [topic_slug]}}
    data = _graphql(query, variables)
    candidates = data["questionList"]["questions"]
    return [
        c for c in candidates
        if not c["isPaidOnly"] and c["titleSlug"] not in exclude_slugs
    ]


def submit_solution(title_slug: str, question_id: str, code: str) -> str:
    body = json.dumps({"lang": "python3", "question_id": question_id, "typed_code": code}).encode()
    headers = {
        **_auth_headers(),
        "Content-Type": "application/json",
        "Referer": f"https://leetcode.com/problems/{title_slug}/",
        "User-Agent": "leetcode-auto-solver/1.0",
    }
    req = urllib.request.Request(
        f"https://leetcode.com/problems/{title_slug}/submit/", data=body, headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["submission_id"]


def poll_submission(submission_id: str, timeout_s: int = 60) -> dict:
    headers = {
        **_auth_headers(),
        "Referer": "https://leetcode.com/",
        "User-Agent": "leetcode-auto-solver/1.0",
    }
    req = urllib.request.Request(
        f"https://leetcode.com/submissions/detail/{submission_id}/check/",
        headers=headers,
        method="GET",
    )
    deadline = time.time() + timeout_s
    while True:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.load(resp)
        if result.get("state") == "SUCCESS":
            return result
        if time.time() > deadline:
            raise TimeoutError(f"submission {submission_id} did not finish within {timeout_s}s")
        time.sleep(2)


def demo():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    q = Question(
        question_id="1", title="Two Sum", title_slug="two-sum", content="desc",
        difficulty="Easy", python3_stub="class Solution: pass", topic_tags=["array"],
    )
    assert q.title_slug == "two-sum"
    candidates = [
        {"titleSlug": "a", "isPaidOnly": False},
        {"titleSlug": "b", "isPaidOnly": True},
        {"titleSlug": "c", "isPaidOnly": False},
    ]
    kept = [c for c in candidates if not c["isPaidOnly"] and c["titleSlug"] not in {"a"}]
    assert [c["titleSlug"] for c in kept] == ["c"]
    print("leetcode_client.py self-check OK")


if __name__ == "__main__":
    demo()

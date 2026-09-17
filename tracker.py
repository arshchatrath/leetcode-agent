"""tracker.json read/update + tracker.md render. Stdlib only."""
import datetime
import json
import os

TRACKER_PATH = os.path.join(os.path.dirname(__file__), "tracker.json")
MARKDOWN_PATH = os.path.join(os.path.dirname(__file__), "tracker.md")

DEFAULT_TOPICS = ["arrays", "strings", "hashmaps", "two_pointers", "dp", "graphs", "trees"]


def load() -> dict:
    if os.path.exists(TRACKER_PATH):
        with open(TRACKER_PATH) as f:
            return json.load(f)
    return {
        "streak_days": 0,
        "last_run_date": None,
        "rotation_index": 0,
        "topics": DEFAULT_TOPICS,
        "solved_slugs": [],
        "runs": [],
    }


def next_topic(data: dict) -> str:
    topics = data["topics"]
    return topics[data["rotation_index"] % len(topics)]


def update_streak(data: dict, today: str) -> None:
    last = data.get("last_run_date")
    if last == today:
        return
    yesterday = (datetime.date.fromisoformat(today) - datetime.timedelta(days=1)).isoformat()
    if last == yesterday:
        data["streak_days"] = data.get("streak_days", 0) + 1
    else:
        data["streak_days"] = 1
    data["last_run_date"] = today


def record_run(data: dict, today: str, problems: list) -> None:
    data["runs"] = [r for r in data["runs"] if r["date"] != today]
    data["runs"].append({"date": today, "problems": problems})
    solved = set(data["solved_slugs"])
    for p in problems:
        if p["verdict"] == "Accepted":
            solved.add(p["slug"])
    data["solved_slugs"] = sorted(solved)
    data["rotation_index"] = data["rotation_index"] + 1


def render_markdown(data: dict) -> str:
    all_problems = [p for r in data["runs"] for p in r["problems"]]
    attempted = len(all_problems)
    accepted = [p for p in all_problems if p["verdict"] == "Accepted"]
    success_rate = (len(accepted) / attempted * 100) if attempted else 0.0
    avg_attempts = (sum(p["attempts"] for p in accepted) / len(accepted)) if accepted else 0.0

    topic_counts = {}
    for p in accepted:
        if p.get("topic"):
            topic_counts[p["topic"]] = topic_counts.get(p["topic"], 0) + 1

    lines = [
        "# LeetCode Auto-Solver Tracker",
        f"_generated at {datetime.datetime.now().isoformat(timespec='seconds')}_",
        "",
        f"- **Current streak:** {data.get('streak_days', 0)} day(s)",
        f"- **Next rotation topic:** {next_topic(data)}",
        f"- **Total attempted:** {attempted}",
        f"- **Total accepted:** {len(accepted)}",
        f"- **Success rate:** {success_rate:.1f}%",
        f"- **Avg attempts-to-accept:** {avg_attempts:.2f}",
        "",
        "## Topics solved",
    ]
    if topic_counts:
        for topic, count in sorted(topic_counts.items()):
            lines.append(f"- {topic}: {count}")
    else:
        lines.append("_none yet_")

    lines += ["", "## Recent runs", "", "| date | slug | source | difficulty | topic | verdict | attempts |",
              "|---|---|---|---|---|---|---|"]
    for run in data["runs"][-10:]:
        for p in run["problems"]:
            lines.append(
                f"| {run['date']} | {p['slug']} | {p['source']} | {p['difficulty']} | "
                f"{p.get('topic') or '-'} | {p['verdict']} | {p['attempts']} |"
            )
    return "\n".join(lines) + "\n"


def save(data: dict) -> None:
    with open(TRACKER_PATH, "w") as f:
        json.dump(data, f, indent=2)
    with open(MARKDOWN_PATH, "w") as f:
        f.write(render_markdown(data))


def demo():
    data = {
        "streak_days": 0, "last_run_date": None, "rotation_index": 0,
        "topics": DEFAULT_TOPICS, "solved_slugs": [], "runs": [],
    }
    update_streak(data, "2026-09-01")
    assert data["streak_days"] == 1
    update_streak(data, "2026-09-02")
    assert data["streak_days"] == 2
    update_streak(data, "2026-09-02")
    assert data["streak_days"] == 2
    update_streak(data, "2026-09-10")
    assert data["streak_days"] == 1

    record_run(data, "2026-09-10", [
        {"slug": "two-sum", "source": "daily", "difficulty": "Easy", "topic": None,
         "verdict": "Accepted", "attempts": 1},
    ])
    md = render_markdown(data)
    assert "100.0%" in md
    print("tracker.py self-check OK")


if __name__ == "__main__":
    demo()

"""Daily entrypoint: fetch daily + rotation problem, solve, submit, retry, log, track."""
import argparse
import datetime
import json
import os

import leetcode_client
import solver
import tracker

MAX_ATTEMPTS = 5
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")


def load_dotenv():
    path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def solve_and_submit(question: leetcode_client.Question, dry_run: bool) -> dict:
    attempts_log = []
    approach = ""
    previous_code = None
    verdict_detail = None
    final_verdict = "Failed"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            approach, code = solver.solve(question, previous_code, verdict_detail)
        except ValueError as e:
            attempts_log.append({"attempt": attempt, "error": str(e)})
            previous_code = previous_code or ""
            verdict_detail = {"status_msg": f"Could not parse solver output: {e}"}
            continue

        if dry_run:
            attempts_log.append({"attempt": attempt, "code": code, "verdict": "Skipped (dry-run)"})
            final_verdict = "Skipped (dry-run)"
            break

        submission_id = leetcode_client.submit_solution(question.title_slug, question.question_id, code)
        result = leetcode_client.poll_submission(submission_id)
        attempts_log.append({"attempt": attempt, "code": code, "verdict": result.get("status_msg")})

        if result.get("status_msg") == "Accepted":
            final_verdict = "Accepted"
            break

        previous_code = code
        verdict_detail = result
        final_verdict = "Failed"

    return {
        "approach": approach,
        "attempts_log": attempts_log,
        "final_verdict": final_verdict,
        "attempts": len(attempts_log),
    }


def run_problem(question: leetcode_client.Question, source: str, topic: str, dry_run: bool) -> dict:
    outcome = solve_and_submit(question, dry_run)
    return {
        "slug": question.title_slug,
        "source": source,
        "difficulty": question.difficulty,
        "topic": topic,
        "approach": outcome["approach"],
        "attempts_log": outcome["attempts_log"],
        "verdict": outcome["final_verdict"],
        "attempts": outcome["attempts"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    data = tracker.load()
    today = datetime.date.today().isoformat()

    daily_slug = leetcode_client.get_daily_challenge()
    daily_question = leetcode_client.get_question(daily_slug)
    daily_entry = run_problem(daily_question, "daily", None, args.dry_run)

    topic = tracker.next_topic(data)
    topic_slug = leetcode_client.TOPIC_SLUGS[topic]
    candidates = leetcode_client.list_problems_by_topic(topic_slug, set(data["solved_slugs"]))
    if not candidates:
        raise RuntimeError(f"no unsolved candidates found for topic '{topic}'")
    rotation_question = leetcode_client.get_question(candidates[0]["titleSlug"])
    rotation_entry = run_problem(rotation_question, "rotation", topic, args.dry_run)

    entries = [daily_entry, rotation_entry]

    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, f"{today}.json"), "w") as f:
        json.dump(entries, f, indent=2)

    summaries = [
        {"slug": e["slug"], "source": e["source"], "difficulty": e["difficulty"], "topic": e["topic"],
         "verdict": e["verdict"], "attempts": e["attempts"]}
        for e in entries
    ]
    tracker.update_streak(data, today)
    tracker.record_run(data, today, summaries)
    tracker.save(data)

    for e in entries:
        print(f"[{e['source']}] {e['slug']} ({e['difficulty']}) -> {e['verdict']} in {e['attempts']} attempt(s)")


if __name__ == "__main__":
    main()

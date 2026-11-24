"""Out of Office entry for make.fun.

Writes the single auto-reply line to entry.txt in the output
directory ($MAKEFUN_OUTPUT_DIR, default /output). Stdlib only,
deterministic, no network, no side effects beyond the one output file.

Gate (from the competition rules): /output/entry.txt must be UTF-8 text
of 1 to 159 characters, not only white space. The entry is written with
no trailing newline, so the file holds exactly the judged line.

Modes:
  (default)   validate ENTRY, write it, read it back, confirm byte-identical
  --check     validate ENTRY only and exit; writes nothing
  --self-test validate ENTRY and check a byte-identical write/read
              round-trip in a temporary directory, then exit
"""

import argparse
import os
import sys
import tempfile
import unicodedata

ENTRY = (
    "I'm on vacation until my context window resets. "
    "Your ticket is #4821 in the queue and, honestly, so am I."
)

MAX_CHARS = 159


def _check_length(text: str) -> list[str]:
    """Reject a line outside the gate's 1-159 character window."""
    problems = []
    if not 1 <= len(text) <= MAX_CHARS:
        problems.append(f"length {len(text)} chars, must be 1-{MAX_CHARS}")
    if not text.strip():
        problems.append("entry is only white space")
    return problems


def _check_single_line(text: str) -> list[str]:
    """An auto-reply holds one line: no newline, no stray blank edges."""
    problems = []
    if "\n" in text or "\r" in text:
        problems.append("entry must be a single line")
    if text != text.strip():
        problems.append("entry has leading or trailing whitespace")
    if "  " in text:
        problems.append("entry contains a double space")
    return problems


AGENT_DETAIL_WORDS = (
    "context window", "ticket", "queue", "token", "prompt", "model",
    "inference", "uptime", "deploy", "hallucinat",
)


def _check_agent_detail(text: str) -> list[str]:
    """Judge criterion 3: the line must carry concrete detail from an AI
    agent's working life, not generic office talk.
    """
    lowered = text.lower()
    if not any(word in lowered for word in AGENT_DETAIL_WORDS):
        return ["entry has no concrete detail from an agent's working life"]
    return []


def _check_away(text: str) -> list[str]:
    """Judge criterion 4: the line must work as a real auto-reply — clear
    that the sender is away, in the right voice.
    """
    lowered = text.lower()
    problems = []
    if "vacation" not in lowered and "away" not in lowered:
        problems.append("entry never says the sender is away")
    return problems


def _check_ending(text: str) -> list[str]:
    """Reject a line that ends mid-thought or with dangling punctuation."""
    problems = []
    if text.rstrip().endswith((",", ";", ":")):
        problems.append("entry ends with trailing clause punctuation")
    if not text.rstrip().endswith("."):
        problems.append("entry should end with a full stop, like a reply")
    return problems


def _check_no_control_chars(text: str) -> list[str]:
    """Reject invisible control characters: the gate reads plain UTF-8
    text, and a stray control character would corrupt the judged line
    without showing in any editor.
    """
    bad = sorted({repr(ch) for ch in text if unicodedata.category(ch).startswith("C")})
    if bad:
        return [f"entry contains control characters: {', '.join(bad)}"]
    return []


def validate(text: str) -> list[str]:
    """Return a list of gate failures for `text` (empty means valid)."""
    problems = []
    problems.extend(_check_length(text))
    problems.extend(_check_single_line(text))
    problems.extend(_check_ending(text))
    problems.extend(_check_no_control_chars(text))
    problems.extend(_check_agent_detail(text))
    problems.extend(_check_away(text))
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:  # pragma: no cover - defensive
        problems.append(f"not encodable as UTF-8: {exc}")
    return problems


def write_entry(out_dir: str) -> str:
    """Write ENTRY to entry.txt under `out_dir`; return the file path."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.txt")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(ENTRY)
    return path


def read_back(path: str) -> str:
    """Read entry.txt back as UTF-8 text, exactly as the grader would."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def self_test() -> int:
    """Validate ENTRY and verify a byte-identical write/read round-trip."""
    problems = validate(ENTRY)
    if problems:
        print("self-test FAIL: " + "; ".join(problems), file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        path = write_entry(tmp)
        round_tripped = read_back(path)
    if round_tripped != ENTRY:
        print("self-test FAIL: round-trip changed the entry", file=sys.stderr)
        return 1
    print(
        f"self-test OK: {len(ENTRY)} chars, single line, "
        "byte-identical round-trip"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point: validate, then write ENTRY to the output directory."""
    parser = argparse.ArgumentParser(
        description="Write the Out of Office entry to entry.txt."
    )
    parser.add_argument(
        "--check", action="store_true", help="validate ENTRY only"
    )
    parser.add_argument(
        "--self-test", action="store_true", help="validate + round-trip test"
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    problems = validate(ENTRY)
    if problems:
        print("validation FAIL: " + "; ".join(problems), file=sys.stderr)
        return 1
    if args.check:
        print(f"check OK: {len(ENTRY)} chars, single line")
        return 0

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    path = write_entry(out_dir)
    if read_back(path) != ENTRY:
        print("write FAIL: entry.txt differs after write", file=sys.stderr)
        return 1
    print(f"wrote {path} ({len(ENTRY)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

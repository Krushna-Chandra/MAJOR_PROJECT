import json
import os
import random
import subprocess
import tempfile
import uuid
from typing import Any, Dict, List, Optional

from interview_ai import ProviderError, _generate_json_with_fallback, _normalize_text, _safe_list


RECENT_CHALLENGE_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "coding_question_history.json")
RECENT_CHALLENGE_HISTORY_LIMIT = 200


LANGUAGE_CATALOG: Dict[str, Dict[str, Any]] = {
    "javascript": {
        "label": "JavaScript (Node.js)",
        "file_name": "solution.js",
        "run_templates": [["node", "{file_name}"]],
    },
    "java": {
        "label": "Java",
        "file_name": "Solution.java",
        "compile_templates": [["javac", "{file_name}"]],
        "run_templates": [["java", "Solution"]],
    },
    "python": {
        "label": "Python",
        "file_name": "solution.py",
        "run_templates": [["python", "{file_name}"], ["py", "-3", "{file_name}"], ["py", "{file_name}"]],
    },
    "c": {
        "label": "C",
        "file_name": "solution.c",
        "binary_name": "solution.exe",
        "compile_templates": [
            ["gcc", "{file_name}", "-O2", "-std=c11", "-o", "{binary_path}"],
            ["clang", "{file_name}", "-O2", "-std=c11", "-o", "{binary_path}"],
        ],
        "run_templates": [["{binary_path}"]],
    },
    "cpp": {
        "label": "C++",
        "file_name": "solution.cpp",
        "binary_name": "solution.exe",
        "compile_templates": [
            ["g++", "{file_name}", "-O2", "-std=c++17", "-o", "{binary_path}"],
            ["clang++", "{file_name}", "-O2", "-std=c++17", "-o", "{binary_path}"],
        ],
        "run_templates": [["{binary_path}"]],
    },
    "csharp": {
        "label": "C#",
        "file_name": "Solution.cs",
    },
    "typescript": {
        "label": "TypeScript",
        "file_name": "solution.ts",
    },
    "go": {
        "label": "Go",
        "file_name": "solution.go",
        "run_templates": [["go", "run", "{file_name}"]],
    },
    "rust": {
        "label": "Rust",
        "file_name": "solution.rs",
        "binary_name": "solution.exe",
        "compile_templates": [["rustc", "{file_name}", "-O", "-o", "{binary_path}"]],
        "run_templates": [["{binary_path}"]],
    },
    "php": {
        "label": "PHP",
        "file_name": "solution.php",
        "run_templates": [["php", "{file_name}"]],
    },
    "ruby": {
        "label": "Ruby",
        "file_name": "solution.rb",
        "run_templates": [["ruby", "{file_name}"]],
    },
    "kotlin": {
        "label": "Kotlin",
        "file_name": "Solution.kt",
    },
    "swift": {
        "label": "Swift",
        "file_name": "solution.swift",
    },
}


FALLBACK_CHALLENGES = {
    "easy": [
        {
        "title": "Count Vowels in a String",
        "difficulty": "easy",
        "description": (
            "Given a string, return the number of vowels present in it. "
            "Treat a, e, i, o, and u as vowels and ignore case."
        ),
        "constraints": [
            "1 <= length of input <= 10^5",
            "Input may contain spaces and punctuation",
        ],
        "hints": [
            "Convert the string to lowercase before checking vowels.",
            "A single linear scan is enough.",
        ],
        "examples": [
            {"input": "hello world", "output": "3", "explanation": "The vowels are e, o, o."},
            {"input": "ApIs", "output": "2", "explanation": "The vowels are A and I."},
        ],
        "public_test_cases": [
            {"input": "education", "expected_output": "5"},
            {"input": "rhythm", "expected_output": "0"},
        ],
        "hidden_test_cases": [
            {"input": "Interview Preparation", "expected_output": "9"},
            {"input": "AEIOUxyz", "expected_output": "5"},
        ],
        },
        {
        "title": "Sum of Digits",
        "difficulty": "easy",
        "description": "Given a non-negative integer as input, print the sum of its digits.",
        "constraints": [
            "0 <= n <= 10^18",
            "Input is provided through standard input",
        ],
        "hints": [
            "Process the input as a string or repeatedly extract digits.",
            "A simple linear scan is enough.",
        ],
        "examples": [
            {"input": "482", "output": "14", "explanation": "4 + 8 + 2 = 14."},
            {"input": "9001", "output": "10", "explanation": "9 + 0 + 0 + 1 = 10."},
        ],
        "public_test_cases": [
            {"input": "12345", "expected_output": "15"},
            {"input": "700", "expected_output": "7"},
        ],
        "hidden_test_cases": [
            {"input": "99999", "expected_output": "45"},
            {"input": "0", "expected_output": "0"},
        ],
        },
        {
        "title": "Count Even Numbers in a List",
        "difficulty": "easy",
        "description": "Given a space-separated list of integers, print how many of them are even.",
        "constraints": [
            "1 <= number of integers <= 10^5",
            "Use standard input and output",
        ],
        "hints": [
            "Split the input into numbers and check each value modulo 2.",
            "You only need a running counter.",
        ],
        "examples": [
            {"input": "1 2 3 4 5 6", "output": "3", "explanation": "The even numbers are 2, 4, and 6."},
        ],
        "public_test_cases": [
            {"input": "10 15 20 25", "expected_output": "2"},
            {"input": "7 9 11", "expected_output": "0"},
        ],
        "hidden_test_cases": [
            {"input": "2 4 6 8 10", "expected_output": "5"},
        ],
        },
    ],
    "medium": [
        {
        "title": "Group Anagrams",
        "difficulty": "medium",
        "description": (
            "Given a list of strings, group the anagrams together and print the grouped "
            "result in a deterministic order."
        ),
        "constraints": [
            "1 <= number of strings <= 10^4",
            "Each string contains lowercase English letters",
            "Aim for a hash-map based grouping solution",
        ],
        "hints": [
            "A sorted string or frequency signature can represent a group key.",
            "Sort each group and the final groups for deterministic output.",
        ],
        "examples": [
            {"input": "eat tea tan ate nat bat", "output": "[[ate,eat,tea],[bat],[nat,tan]]", "explanation": "Words with the same sorted signature belong together."},
        ],
        "public_test_cases": [
            {"input": "eat tea tan ate nat bat", "expected_output": "[[ate,eat,tea],[bat],[nat,tan]]"},
            {"input": "abc bca cab foo oof", "expected_output": "[[abc,bca,cab],[foo,oof]]"},
        ],
        "hidden_test_cases": [
            {"input": "listen silent enlist google gogole", "expected_output": "[[enlist,listen,silent],[gogole,google]]"},
        ],
        },
        {
        "title": "Product of Array Except Self",
        "difficulty": "medium",
        "description": "Given a space-separated list of integers, print the product of array except self for each position.",
        "constraints": [
            "2 <= number of integers <= 10^5",
            "Do not use division",
            "Use standard input and output",
        ],
        "hints": [
            "Build prefix and suffix products.",
            "Each answer is prefix[i] * suffix[i].",
        ],
        "examples": [
            {"input": "1 2 3 4", "output": "24 12 8 6", "explanation": "Each position gets the product of all other values."},
        ],
        "public_test_cases": [
            {"input": "2 3 4 5", "expected_output": "60 40 30 24"},
            {"input": "3 1 2", "expected_output": "2 6 3"},
        ],
        "hidden_test_cases": [
            {"input": "1 1 1 1", "expected_output": "1 1 1 1"},
        ],
        },
        {
        "title": "Longest Consecutive Run",
        "difficulty": "medium",
        "description": "Given a space-separated list of integers, print the length of the longest consecutive sequence.",
        "constraints": [
            "1 <= number of integers <= 10^5",
            "Aim for near O(n) time",
        ],
        "hints": [
            "Use a set for fast lookups.",
            "Start counting only when a number does not have a predecessor.",
        ],
        "examples": [
            {"input": "100 4 200 1 3 2", "output": "4", "explanation": "The longest consecutive sequence is 1,2,3,4."},
        ],
        "public_test_cases": [
            {"input": "9 1 4 7 3 2 6 8 0", "expected_output": "5"},
            {"input": "1 2 0 1", "expected_output": "3"},
        ],
        "hidden_test_cases": [
            {"input": "5 6 7 20 21", "expected_output": "3"},
        ],
        },
    ],
    "hard": [
        {
        "title": "Longest Unique Substring Length",
        "difficulty": "hard",
        "description": (
            "Given a string, print the length of the longest substring without repeating characters."
        ),
        "constraints": [
            "1 <= length of input <= 2 * 10^5",
            "Aim for an O(n) sliding-window solution",
        ],
        "hints": [
            "Track the latest index of each character.",
            "Move the left pointer only forward.",
        ],
        "examples": [
            {"input": "abcabcbb", "output": "3", "explanation": "abc is the longest substring without duplicates."},
            {"input": "pwwkew", "output": "3", "explanation": "wke is one valid longest substring."},
        ],
        "public_test_cases": [
            {"input": "bbbbb", "expected_output": "1"},
            {"input": "dvdf", "expected_output": "3"},
        ],
        "hidden_test_cases": [
            {"input": "abba", "expected_output": "2"},
            {"input": "abcdefga", "expected_output": "7"},
        ],
        },
        {
        "title": "Minimum Window Substring Length",
        "difficulty": "hard",
        "description": "Given two strings s and t separated by a newline, print the length of the minimum window in s that contains all characters of t. Print 0 if no such window exists.",
        "constraints": [
            "1 <= |s|, |t| <= 2 * 10^5",
            "Aim for an O(n) sliding-window solution",
        ],
        "hints": [
            "Track character frequencies required by t.",
            "Shrink the window only after all requirements are satisfied.",
        ],
        "examples": [
            {"input": "ADOBECODEBANC\nABC", "output": "4", "explanation": "BANC is the minimum valid window."},
        ],
        "public_test_cases": [
            {"input": "a\n a", "expected_output": "1"},
            {"input": "a\n aa", "expected_output": "0"},
        ],
        "hidden_test_cases": [
            {"input": "aaabdabcefaecbef\nabc", "expected_output": "3"},
        ],
        },
        {
        "title": "Largest Rectangle in Histogram",
        "difficulty": "hard",
        "description": "Given space-separated bar heights of a histogram, print the area of the largest rectangle.",
        "constraints": [
            "1 <= number of bars <= 2 * 10^5",
            "Aim for an O(n) stack-based solution",
        ],
        "hints": [
            "Use a monotonic increasing stack.",
            "When a lower bar appears, resolve rectangles ending at previous bars.",
        ],
        "examples": [
            {"input": "2 1 5 6 2 3", "output": "10", "explanation": "The largest rectangle uses heights 5 and 6."},
        ],
        "public_test_cases": [
            {"input": "2 4", "expected_output": "4"},
            {"input": "6 2 5 4 5 1 6", "expected_output": "12"},
        ],
        "hidden_test_cases": [
            {"input": "1 1 1 1", "expected_output": "4"},
        ],
        },
    ],
}


def _pick_fallback_challenge(difficulty: str) -> Dict[str, Any]:
    options = FALLBACK_CHALLENGES.get(difficulty) or FALLBACK_CHALLENGES["easy"]
    return dict(random.choice(options))


def _challenge_key(challenge: Dict[str, Any]) -> str:
    title = _normalize_text(str(challenge.get("title") or "")).lower()
    description = _normalize_text(str(challenge.get("description") or "")).lower()
    return title or description


def _load_recent_challenge_history() -> Dict[str, List[str]]:
    try:
        with open(RECENT_CHALLENGE_HISTORY_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

    if not isinstance(payload, dict):
        return {}

    cleaned: Dict[str, List[str]] = {}
    for difficulty, items in payload.items():
        if isinstance(items, list):
            cleaned[str(difficulty)] = [str(item).strip().lower() for item in items if str(item).strip()]
    return cleaned


def _save_recent_challenge_history(history: Dict[str, List[str]]) -> None:
    try:
        with open(RECENT_CHALLENGE_HISTORY_PATH, "w", encoding="utf-8") as handle:
            json.dump(history, handle, ensure_ascii=False, indent=2)
    except OSError:
        return


def _recent_challenge_keys(difficulty: str) -> List[str]:
    history = _load_recent_challenge_history()
    normalized_difficulty = str(difficulty or "easy").lower()
    return history.get(normalized_difficulty, [])


def _remember_recent_challenge(difficulty: str, challenge: Dict[str, Any]) -> None:
    key = _challenge_key(challenge)
    if not key:
        return

    normalized_difficulty = str(difficulty or "easy").lower()
    history = _load_recent_challenge_history()
    items = [item for item in history.get(normalized_difficulty, []) if item != key]
    items.append(key)
    history[normalized_difficulty] = items[-RECENT_CHALLENGE_HISTORY_LIMIT:]
    _save_recent_challenge_history(history)


FALLBACK_VARIANTS: Dict[str, List[Dict[str, Any]]] = {
    "easy": [
        {
            "title": "Count Words With Vowels",
            "description": "Given a line of text, print how many words contain at least one vowel.",
            "constraints": ["1 <= number of words <= 10^5", "Treat vowels case-insensitively"],
            "hints": ["Split by whitespace.", "Check each word for a, e, i, o, u."],
            "examples": [{"input": "sky apple dry orange", "output": "2", "explanation": "Only apple and orange contain vowels."}],
            "public_test_cases": [{"input": "code gym fly", "expected_output": "1"}, {"input": "a e i", "expected_output": "3"}],
            "hidden_test_cases": [{"input": "rhythm crypt why", "expected_output": "0"}],
        },
        {
            "title": "Largest Digit in a Number",
            "description": "Given a non-negative integer, print the largest digit present in it.",
            "constraints": ["0 <= n <= 10^18"],
            "hints": ["Process the number digit by digit or as a string."],
            "examples": [{"input": "48219", "output": "9", "explanation": "9 is the largest digit."}],
            "public_test_cases": [{"input": "700", "expected_output": "7"}, {"input": "12345", "expected_output": "5"}],
            "hidden_test_cases": [{"input": "0", "expected_output": "0"}],
        },
        {
            "title": "Count Positive Numbers",
            "description": "Given a space-separated list of integers, print how many numbers are greater than zero.",
            "constraints": ["1 <= number of integers <= 10^5"],
            "hints": ["Split the input and count values above zero."],
            "examples": [{"input": "-1 0 4 7 -3", "output": "2", "explanation": "Only 4 and 7 are positive."}],
            "public_test_cases": [{"input": "1 2 3", "expected_output": "3"}, {"input": "-5 -2 0", "expected_output": "0"}],
            "hidden_test_cases": [{"input": "9 -1 8 -2 7", "expected_output": "3"}],
        },
        {
            "title": "Reverse Each Word",
            "description": "Given a sentence, reverse every word individually while preserving word order.",
            "constraints": ["1 <= length of input <= 10^5"],
            "hints": ["Split into words, reverse each word, then join."],
            "examples": [{"input": "code daily", "output": "edoc yliad", "explanation": "Each word is reversed in place."}],
            "public_test_cases": [{"input": "hello world", "expected_output": "olleh dlrow"}, {"input": "a bc def", "expected_output": "a cb fed"}],
            "hidden_test_cases": [{"input": "AI mock interview", "expected_output": "IA kcom weivretni"}],
        },
        {
            "title": "Second Largest Number",
            "description": "Given a space-separated list of distinct integers, print the second largest value.",
            "constraints": ["2 <= number of integers <= 10^5", "All values are distinct"],
            "hints": ["Track the largest and second largest values while scanning."],
            "examples": [{"input": "3 8 2 10 6", "output": "8", "explanation": "10 is largest, so 8 is second largest."}],
            "public_test_cases": [{"input": "1 9", "expected_output": "1"}, {"input": "4 7 2 11 5", "expected_output": "7"}],
            "hidden_test_cases": [{"input": "100 90 80 70", "expected_output": "90"}],
        },
    ],
    "medium": [
        {
            "title": "Top K Frequent Numbers",
            "description": "Given a space-separated list of integers and a final integer k on the next line, print the k most frequent numbers in descending frequency order, breaking ties by smaller number first.",
            "constraints": ["1 <= n <= 10^5", "1 <= k <= number of distinct values"],
            "hints": ["Count frequencies with a hash map.", "Sort by frequency, then by value."],
            "examples": [{"input": "1 1 1 2 2 3\n2", "output": "1 2", "explanation": "1 appears three times and 2 appears twice."}],
            "public_test_cases": [{"input": "4 4 4 6 6 8\n2", "expected_output": "4 6"}, {"input": "5 5 1 1 2 2\n1", "expected_output": "1"}],
            "hidden_test_cases": [{"input": "9 8 8 7 7 7 6 6 6 6\n3", "expected_output": "6 7 8"}],
        },
        {
            "title": "Merge Overlapping Intervals",
            "description": "Given intervals as lines of 'start end', merge all overlapping intervals and print the merged intervals in order.",
            "constraints": ["1 <= number of intervals <= 10^5"],
            "hints": ["Sort by start time.", "Expand the current interval while overlaps continue."],
            "examples": [{"input": "1 3\n2 6\n8 10\n15 18", "output": "1 6\n8 10\n15 18", "explanation": "The first two intervals overlap and merge."}],
            "public_test_cases": [{"input": "1 4\n4 5", "expected_output": "1 5"}, {"input": "1 2\n3 4", "expected_output": "1 2\n3 4"}],
            "hidden_test_cases": [{"input": "2 3\n5 7\n6 8\n9 10", "expected_output": "2 3\n5 8\n9 10"}],
        },
        {
            "title": "Longest Subarray With Sum K",
            "description": "Given a space-separated list of integers and a target k on the next line, print the length of the longest contiguous subarray whose sum equals k.",
            "constraints": ["1 <= n <= 10^5", "-10^9 <= values <= 10^9"],
            "hints": ["Use prefix sums.", "Store the earliest index for each prefix sum."],
            "examples": [{"input": "1 -1 5 -2 3\n3", "output": "4", "explanation": "The subarray [1, -1, 5, -2] sums to 3."}],
            "public_test_cases": [{"input": "-2 -1 2 1\n1", "expected_output": "2"}, {"input": "2 3 1 2 4 3\n7", "expected_output": "3"}],
            "hidden_test_cases": [{"input": "1 2 3 4 5\n9", "expected_output": "3"}],
        },
        {
            "title": "Validate Bracket Sequence",
            "description": "Given a string containing only brackets (), {}, and [], print Valid if the sequence is balanced, otherwise print Invalid.",
            "constraints": ["1 <= length <= 10^5"],
            "hints": ["Use a stack.", "Match every closing bracket with the latest opening bracket."],
            "examples": [{"input": "{[()]}", "output": "Valid", "explanation": "All brackets close in the correct order."}],
            "public_test_cases": [{"input": "([)]", "expected_output": "Invalid"}, {"input": "(()[])", "expected_output": "Valid"}],
            "hidden_test_cases": [{"input": "]", "expected_output": "Invalid"}],
        },
        {
            "title": "Spiral Order of Matrix",
            "description": "Given a matrix where each line is a row of space-separated integers, print the elements in spiral order.",
            "constraints": ["1 <= rows, cols <= 100"],
            "hints": ["Track top, bottom, left, and right boundaries."],
            "examples": [{"input": "1 2 3\n4 5 6\n7 8 9", "output": "1 2 3 6 9 8 7 4 5", "explanation": "Traverse layer by layer in spiral order."}],
            "public_test_cases": [{"input": "1 2\n3 4", "expected_output": "1 2 4 3"}, {"input": "1 2 3 4", "expected_output": "1 2 3 4"}],
            "hidden_test_cases": [{"input": "1\n2\n3", "expected_output": "1 2 3"}],
        },
    ],
    "hard": [
        {
            "title": "Sliding Window Maximum",
            "description": "Given a space-separated list of integers and a window size k on the next line, print the maximum for every sliding window of size k.",
            "constraints": ["1 <= n <= 2 * 10^5", "1 <= k <= n"],
            "hints": ["Use a deque to keep useful indices.", "Discard out-of-window indices from the front."],
            "examples": [{"input": "1 3 -1 -3 5 3 6 7\n3", "output": "3 3 5 5 6 7", "explanation": "Each output is the max of one window of size 3."}],
            "public_test_cases": [{"input": "9 8 7 6 5\n2", "expected_output": "9 8 7 6"}, {"input": "4 2 12 3\n1", "expected_output": "4 2 12 3"}],
            "hidden_test_cases": [{"input": "2 1 2 4 3\n3", "expected_output": "2 4 4"}],
        },
        {
            "title": "Trapping Rain Water",
            "description": "Given space-separated bar heights, print the total units of water trapped after raining.",
            "constraints": ["1 <= number of bars <= 2 * 10^5"],
            "hints": ["Use two pointers or prefix/suffix max arrays.", "Water at each index depends on the lower boundary."],
            "examples": [{"input": "0 1 0 2 1 0 1 3 2 1 2 1", "output": "6", "explanation": "The histogram traps 6 units of water."}],
            "public_test_cases": [{"input": "4 2 0 3 2 5", "expected_output": "9"}, {"input": "1 2 3 4", "expected_output": "0"}],
            "hidden_test_cases": [{"input": "5 4 1 2", "expected_output": "1"}],
        },
        {
            "title": "Median of Running Stream",
            "description": "Given a stream of integers as a space-separated list, print the median after each insertion.",
            "constraints": ["1 <= n <= 10^5"],
            "hints": ["Maintain two heaps.", "Balance sizes after each insertion."],
            "examples": [{"input": "5 15 1 3", "output": "5 10 5 4", "explanation": "The running medians are 5, 10, 5, and 4."}],
            "public_test_cases": [{"input": "2 4 6", "expected_output": "2 3 4"}, {"input": "1 1 1", "expected_output": "1 1 1"}],
            "hidden_test_cases": [{"input": "7 3 5 9", "expected_output": "7 5 5 6"}],
        },
        {
            "title": "Word Ladder Steps",
            "description": "Given a begin word, end word, and a dictionary of lowercase words on separate lines, print the minimum number of transformations needed to reach the end word, changing one letter at a time. Print 0 if impossible.",
            "constraints": ["All words have the same length.", "1 <= dictionary size <= 5000"],
            "hints": ["Breadth-first search works well.", "Generate one-letter transformations efficiently."],
            "examples": [{"input": "hit\ncog\nhot dot dog lot log cog", "output": "5", "explanation": "One shortest path is hit -> hot -> dot -> dog -> cog."}],
            "public_test_cases": [{"input": "hit\ncog\nhot dot dog lot log cog", "expected_output": "5"}, {"input": "hit\ncog\nhot dot dog lot log", "expected_output": "0"}],
            "hidden_test_cases": [{"input": "a\nc\na b c", "expected_output": "2"}],
        },
        {
            "title": "Alien Dictionary Order",
            "description": "Given sorted dictionary words from an alien language, print one valid character order. Print Invalid if no order exists.",
            "constraints": ["1 <= number of words <= 10^4"],
            "hints": ["Build a graph from the first differing character between adjacent words.", "Use topological sorting."],
            "examples": [{"input": "baa abcd abca cab cad", "output": "bdac", "explanation": "bdac is one valid topological ordering."}],
            "public_test_cases": [{"input": "caa aaa aab", "expected_output": "cab"}, {"input": "abc ab", "expected_output": "Invalid"}],
            "hidden_test_cases": [{"input": "z x z", "expected_output": "Invalid"}],
        },
    ],
}


def _pick_unique_fallback_challenge(difficulty: str, excluded_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    excluded = set((excluded_keys or []))
    combined = [dict(item) for item in (FALLBACK_VARIANTS.get(difficulty) or [])] + [dict(item) for item in (FALLBACK_CHALLENGES.get(difficulty) or FALLBACK_CHALLENGES["easy"])]
    random.shuffle(combined)
    for item in combined:
        if _challenge_key(item) not in excluded:
            return item
    return dict(random.choice(combined if combined else FALLBACK_CHALLENGES["easy"]))


def _resolve_template(candidates: List[List[str]]) -> Optional[List[str]]:
    for template in candidates:
        if template and shutil_which(template[0]):
            return template
    return None


def shutil_which(command: str) -> Optional[str]:
    from shutil import which

    return which(command)


def _build_command(template: List[str], context: Dict[str, str]) -> List[str]:
    return [part.format(**context) for part in template]


def _language_status(language_id: str) -> Dict[str, Any]:
    config = LANGUAGE_CATALOG[language_id]
    compile_template = _resolve_template(config.get("compile_templates") or [])
    run_template = _resolve_template(config.get("run_templates") or [])
    available = bool(run_template) and (
        not config.get("compile_templates") or bool(compile_template)
    )
    return {
        "id": language_id,
        "label": config["label"],
        "available": available,
    }


def _starter_code_for_challenge(challenge: Dict[str, Any]) -> Dict[str, str]:
    title = _normalize_text(challenge.get("title") or "Coding Challenge")
    return {
        "javascript": f"""// {title}
// Read from stdin and print the final answer to stdout.

const fs = require("fs");
const input = fs.readFileSync(0, "utf8").trim();

function solve(rawInput) {{
  return "";
}}

const result = solve(input);
process.stdout.write(String(result).trim());
""",
        "java": f"""import java.io.*;

public class Solution {{
    static String solve(String input) {{
        return "";
    }}

    public static void main(String[] args) throws Exception {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        StringBuilder sb = new StringBuilder();
        String line;
        boolean first = true;
        while ((line = br.readLine()) != null) {{
            if (!first) sb.append("\\n");
            sb.append(line);
            first = false;
        }}
        System.out.print(solve(sb.toString().trim()).trim());
    }}
}}
""",
        "python": f"""# {title}
# Read from stdin and print the final answer to stdout.

import sys


def solve(raw_input: str) -> str:
    # Write your solution here
    return ""


if __name__ == "__main__":
    print(str(solve(sys.stdin.read().strip())).strip())
""",
        "c": f"""/* {title} */
#include <stdio.h>
#include <string.h>

char* solve(const char* input) {{
    /* Write your solution here */
    return "";
}}

int main(void) {{
    char input[100000];
    size_t length = fread(input, 1, sizeof(input) - 1, stdin);
    input[length] = '\\0';
    printf("%s", solve(input));
    return 0;
}}
""",
        "cpp": f"""// {title}
#include <bits/stdc++.h>
using namespace std;

string solve(const string& input) {{
    // Write your solution here
    return "";
}}

int main() {{
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input(
        (istreambuf_iterator<char>(cin)),
        istreambuf_iterator<char>()
    );
    cout << solve(input);
    return 0;
}}
""",
        "csharp": f"""// {title}
using System;

public class Solution {{
    static string Solve(string input) {{
        // Write your solution here
        return "";
    }}

    public static void Main() {{
        string input = Console.In.ReadToEnd().Trim();
        Console.Write(Solve(input).Trim());
    }}
}}
""",
        "typescript": f"""// {title}
import * as fs from "fs";
const input = fs.readFileSync(0, "utf8").trim();

function solve(rawInput: string): string {{
    // Write your solution here
    return "";
}}

process.stdout.write(String(solve(input)).trim());
""",
        "go": f"""// {title}
package main

import (
    "fmt"
    "io"
    "os"
    "strings"
)

func solve(input string) string {{
    // Write your solution here
    return ""
}}

func main() {{
    data, _ := io.ReadAll(os.Stdin)
    fmt.Print(strings.TrimSpace(solve(strings.TrimSpace(string(data)))))
}}
""",
        "rust": f"""// {title}
use std::io::Read;

fn solve(input: &str) -> String {{
    // Write your solution here
    String::new()
}}

fn main() {{
    let mut input = String::new();
    std::io::stdin().read_to_string(&mut input).unwrap();
    print!("{{}}", solve(input.trim()));
}}
""",
        "php": f"""<?php
// {title}

function solve(string $input): string {{
    // Write your solution here
    return "";
}}

$input = trim(stream_get_contents(STDIN));
echo trim(solve($input));
""",
        "ruby": f"""# {title}

def solve(input)
  # Write your solution here
  ""
end

input = STDIN.read.strip
print solve(input).strip
""",
        "kotlin": f"""// {title}
fun solve(input: String): String {{
    // Write your solution here
    return ""
}}

fun main() {{
    val input = generateSequence(::readLine).joinToString("\\n").trim()
    print(solve(input).trim())
}}
""",
        "swift": f"""// {title}
import Foundation

func solve(_ input: String) -> String {{
    // Write your solution here
    return ""
}}

let input = String(data: FileHandle.standardInput.readDataToEndOfFile(), encoding: .utf8) ?? ""
print(solve(input.trimmingCharacters(in: .whitespacesAndNewlines)))
""",
    }


def _normalize_challenge(raw: Dict[str, Any], difficulty: str) -> Dict[str, Any]:
    fallback = _pick_unique_fallback_challenge(difficulty)
    title = _normalize_text(raw.get("title") or fallback["title"])
    description = _normalize_text(raw.get("description") or fallback["description"])
    constraints = _safe_list(raw.get("constraints")) or fallback["constraints"]
    hints = _safe_list(raw.get("hints")) or fallback["hints"]
    examples = raw.get("examples") if isinstance(raw.get("examples"), list) else fallback["examples"]
    public_test_cases = raw.get("public_test_cases") if isinstance(raw.get("public_test_cases"), list) else fallback["public_test_cases"]
    hidden_test_cases = raw.get("hidden_test_cases") if isinstance(raw.get("hidden_test_cases"), list) else fallback["hidden_test_cases"]

    def normalize_case(item: Any) -> Dict[str, str]:
        if not isinstance(item, dict):
            return {"input": "", "output": "", "expected_output": ""}
        input_text = _normalize_text(str(item.get("input") or ""))
        output_text = _normalize_text(str(item.get("output") or item.get("expected_output") or ""))
        explanation = _normalize_text(str(item.get("explanation") or ""))
        return {
            "input": input_text,
            "output": output_text,
            "expected_output": output_text,
            "explanation": explanation,
        }

    challenge = {
        "id": uuid.uuid4().hex,
        "title": title,
        "difficulty": difficulty,
        "description": description,
        "constraints": constraints[:5],
        "hints": hints[:4],
        "examples": [normalize_case(item) for item in examples[:3]],
        "public_test_cases": [normalize_case(item) for item in public_test_cases[:4]],
        "hidden_test_cases": [normalize_case(item) for item in hidden_test_cases[:6]],
    }
    challenge["starter_code"] = _starter_code_for_challenge(challenge)
    return challenge


async def generate_coding_challenge(difficulty: str = "easy", excluded_questions: Optional[List[str]] = None) -> Dict[str, Any]:
    requested = str(difficulty).lower()
    if requested in {"hard", "advanced"}:
        normalized_difficulty = "hard"
    elif requested in {"medium", "intermediate"}:
        normalized_difficulty = "medium"
    else:
        normalized_difficulty = "easy"
    recent_keys = _recent_challenge_keys(normalized_difficulty)
    exclusions = [item.strip() for item in (excluded_questions or []) if str(item).strip()]
    exclusions.extend(recent_keys)
    exclusion_block = ""
    if exclusions:
        exclusion_block = f"\n- Do not generate a problem that matches or closely resembles any of these prior questions/titles/descriptions: {json.dumps(exclusions[:200], ensure_ascii=False)}.\n"

    excluded_keys = {item.strip().lower() for item in exclusions if item.strip()}
    base_prompt = f"""
You are generating a coding interview problem.

Return valid JSON with this exact shape:
{{
  "title": "short problem title",
  "description": "clear problem statement in plain English",
  "constraints": ["constraint 1", "constraint 2"],
  "hints": ["hint 1", "hint 2"],
  "examples": [
    {{
      "input": "example input",
      "output": "expected output",
      "explanation": "brief explanation"
    }}
  ],
  "public_test_cases": [
    {{
      "input": "stdin input",
      "expected_output": "stdout output"
    }}
  ],
  "hidden_test_cases": [
    {{
      "input": "stdin input",
      "expected_output": "stdout output"
    }}
  ]
}}

Rules:
- Difficulty must be {normalized_difficulty}.
- Make the problem suitable for coding platforms like LeetCode or GeeksforGeeks.
- The problem must be solvable through standard input/output.
- Keep public test cases visible and hidden test cases strong enough for evaluation.
- Generate a fresh problem idea, not a paraphrase of an old one.{exclusion_block}
- Avoid markdown fences.
"""
    for attempt in range(6):
        prompt = f"{base_prompt}\n- Freshness seed: {uuid.uuid4().hex}\n- Attempt number: {attempt + 1}\n"
        try:
            challenge, _provider = await _generate_json_with_fallback(
                prompt,
                ["gemini", "ollama"],
                0.3,
                25,
            )
            normalized = _normalize_challenge(challenge, normalized_difficulty)
            if _challenge_key(normalized) not in excluded_keys:
                _remember_recent_challenge(normalized_difficulty, normalized)
                return normalized
        except ProviderError:
            continue

    fallback = _normalize_challenge(
        _pick_unique_fallback_challenge(normalized_difficulty, list(excluded_keys)),
        normalized_difficulty,
    )
    _remember_recent_challenge(normalized_difficulty, fallback)
    return fallback


def _run_process(command: List[str], cwd: str, stdin_text: str = "", timeout_seconds: int = 6) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        input=stdin_text,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        shell=False,
    )


def run_code_against_tests(language: str, source_code: str, test_cases: List[Dict[str, str]]) -> Dict[str, Any]:
    config = LANGUAGE_CATALOG.get(language)
    if not config:
        raise ProviderError("Unsupported programming language.")

    compile_template = _resolve_template(config.get("compile_templates") or [])
    run_template = _resolve_template(config.get("run_templates") or [])
    if not run_template or (config.get("compile_templates") and not compile_template):
        raise ProviderError(f"{config['label']} runtime is not available on this machine.")

    with tempfile.TemporaryDirectory(prefix="apis-coding-") as temp_dir:
        file_name = config["file_name"]
        source_path = os.path.join(temp_dir, file_name)
        binary_path = os.path.join(temp_dir, config.get("binary_name") or "solution.exe")
        context = {
            "workdir": temp_dir,
            "file_name": file_name,
            "source_path": source_path,
            "binary_path": binary_path,
        }

        with open(source_path, "w", encoding="utf-8") as handle:
            handle.write(source_code)

        if compile_template:
            compile_result = _run_process(_build_command(compile_template, context), temp_dir, timeout_seconds=8)
            if compile_result.returncode != 0:
                return {
                    "status": "compile_error",
                    "compile_output": (compile_result.stderr or compile_result.stdout or "").strip(),
                    "passed": 0,
                    "total": len(test_cases),
                    "results": [],
                }

        results = []
        passed = 0
        command = _build_command(run_template, context)
        for index, case in enumerate(test_cases):
            try:
                result = _run_process(command, temp_dir, stdin_text=str(case.get("input") or ""), timeout_seconds=6)
                output = (result.stdout or "").strip()
                stderr = (result.stderr or "").strip()
                expected = (case.get("expected_output") or case.get("output") or "").strip()
                is_pass = result.returncode == 0 and output == expected
                if is_pass:
                    passed += 1
                results.append({
                    "index": index + 1,
                    "input": case.get("input") or "",
                    "expected_output": expected,
                    "actual_output": output,
                    "stderr": stderr,
                    "passed": is_pass,
                })
            except subprocess.TimeoutExpired:
                results.append({
                    "index": index + 1,
                    "input": case.get("input") or "",
                    "expected_output": (case.get("expected_output") or "").strip(),
                    "actual_output": "",
                    "stderr": "Execution timed out.",
                    "passed": False,
                })

        return {
            "status": "ok",
            "passed": passed,
            "total": len(test_cases),
            "results": results,
        }


def merge_execution_results(public_execution: Dict[str, Any], hidden_execution: Dict[str, Any]) -> Dict[str, Any]:
    public_results = list(public_execution.get("results") or [])
    hidden_results = list(hidden_execution.get("results") or [])
    offset = len(public_results)

    normalized_hidden_results = []
    for index, item in enumerate(hidden_results, start=1):
        normalized_hidden_results.append({
            **item,
            "index": offset + index,
        })

    merged_results = public_results + normalized_hidden_results
    passed = int(public_execution.get("passed", 0) or 0) + int(hidden_execution.get("passed", 0) or 0)
    total = int(public_execution.get("total", 0) or 0) + int(hidden_execution.get("total", 0) or 0)
    status = "compile_error" if "compile_error" in {public_execution.get("status"), hidden_execution.get("status")} else "ok"

    response = {
        "status": status,
        "passed": passed,
        "total": total,
        "results": merged_results,
    }

    compile_output = public_execution.get("compile_output") or hidden_execution.get("compile_output")
    if compile_output:
        response["compile_output"] = compile_output
    return response


async def evaluate_coding_submission(
    challenge: Dict[str, Any],
    language: str,
    source_code: str,
    execution_summary: Dict[str, Any],
) -> Dict[str, Any]:
    fallback = build_fallback_coding_review(execution_summary)
    prompt = f"""
You are reviewing a coding interview submission.

Challenge title: {_normalize_text(challenge.get("title") or "")}
Difficulty: {_normalize_text(challenge.get("difficulty") or "")}
Problem: {_normalize_text(challenge.get("description") or "")}
Constraints: {json.dumps(challenge.get("constraints") or [])}
Hints: {json.dumps(challenge.get("hints") or [])}
Language: {language}
Passed tests: {execution_summary.get("passed", 0)} / {execution_summary.get("total", 0)}
Execution results: {json.dumps(execution_summary.get("results") or [], ensure_ascii=False)}
Code:
{source_code[:8000]}

Return valid JSON:
{{
  "summary": "2 to 4 sentence review",
  "strengths": ["up to 3 strengths"],
  "issues": ["up to 3 issues"],
  "complexity": "short time/space complexity note",
  "next_steps": ["up to 3 improvements"]
}}
"""
    try:
        review, _provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.2,
            20,
        )
        return {
            "summary": _normalize_text(review.get("summary") or fallback["summary"]),
            "strengths": _safe_list(review.get("strengths"))[:3] or fallback["strengths"],
            "issues": _safe_list(review.get("issues"))[:3] or fallback["issues"],
            "complexity": _normalize_text(review.get("complexity") or fallback["complexity"]),
            "next_steps": _safe_list(review.get("next_steps"))[:3] or fallback["next_steps"],
        }
    except ProviderError:
        return fallback


def build_fallback_coding_review(execution_summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "summary": (
            "The submission was evaluated against the platform test cases. "
            f"It passed {execution_summary.get('passed', 0)} out of {execution_summary.get('total', 0)} tests."
        ),
        "strengths": [
            "The solution was submitted in runnable code form.",
            "The code was executed against platform test cases.",
        ],
        "issues": [
            "Review the failing test cases and edge conditions.",
        ] if execution_summary.get("passed", 0) < execution_summary.get("total", 0) else [
            "Consider improving code clarity and edge-case explanation."
        ],
        "complexity": "Review algorithmic complexity based on your chosen approach.",
        "next_steps": [
            "Handle uncovered edge cases.",
            "Refactor for readability if needed.",
        ],
    }


def get_coding_runtime_status() -> Dict[str, Any]:
    languages = [_language_status(language_id) for language_id in LANGUAGE_CATALOG]
    return {
        "languages": languages,
    }

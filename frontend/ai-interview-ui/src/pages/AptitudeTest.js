import React, { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { Info } from "lucide-react";
import "../App.css";
import MiniNavbar from "../components/MiniNavbar";
import aptitudeHero from "../assets/aptitude.png";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";
const CODING_HISTORY_KEY = "apis-coding-question-history";
const CODING_POOL_KEY = "apis-coding-question-pool";
const HIDDEN_LANGUAGE_IDS = new Set(["go", "rust", "php", "ruby", "kotlin", "swift"]);

const SECTION_OPTIONS = [
  { id: "aptitude", title: "Aptitude", mode: "mcq", description: "Quantitative practice with arithmetic, percentage, ratio, averages, and data questions." },
  { id: "reasoning", title: "Reasoning", mode: "mcq", description: "Series, coding-decoding, analogy, arrangement, and logic-based questions." },
  { id: "verbal", title: "Qualitative / Verbal", mode: "mcq", description: "Vocabulary, grammar, fill-in-the-blanks, punctuation, and comprehension practice." },
  { id: "coding", title: "Coding", mode: "coding", description: "Choose a coding level and solve multiple AI-generated coding questions in a platform-style editor." },
];

const CODING_LEVELS = [
  { id: "easy", title: "Easy", timerMinutes: 10, description: "Beginner-friendly DSA problems with straightforward logic and basic optimization." },
  { id: "medium", title: "Medium", timerMinutes: 12, description: "Interview-style coding questions with stronger edge cases and cleaner implementation needs." },
  { id: "hard", title: "Hard", timerMinutes: 15, description: "More challenging coding problems that need stronger reasoning and optimization." },
];

const QUESTION_BANKS = {
  aptitude: [
    { question: "What is 15% of 240?", options: ["24", "30", "36", "42"], answer: "36" },
    { question: "The average of 12, 18, 20, and 30 is:", options: ["18", "20", "22", "24"], answer: "20" },
    { question: "A train travels 180 km in 3 hours. What is its speed?", options: ["50 km/h", "55 km/h", "60 km/h", "65 km/h"], answer: "60 km/h" },
    { question: "What is 3/4 of 84?", options: ["56", "60", "63", "66"], answer: "63" },
    { question: "What is 18 squared?", options: ["288", "304", "324", "342"], answer: "324" },
    { question: "What is 40% of 350?", options: ["120", "130", "140", "150"], answer: "140" },
    { question: "If 25% of a number is 75, the number is:", options: ["250", "275", "300", "325"], answer: "300" },
    { question: "What is the area of a rectangle with length 15 cm and breadth 8 cm?", options: ["100", "110", "120", "130"], answer: "120" },
    { question: "What is 11% of 900?", options: ["89", "95", "99", "101"], answer: "99" },
    { question: "What is the cube of 4?", options: ["16", "32", "48", "64"], answer: "64" },
  ],
  reasoning: [
    { question: "Find the next number: 3, 6, 12, 24, ?", options: ["30", "36", "42", "48"], answer: "48" },
    { question: "Odd one out: Circle, Triangle, Square, Table", options: ["Circle", "Square", "Table", "Triangle"], answer: "Table" },
    { question: "If CAT is coded as DBU, how is DOG coded?", options: ["EPH", "EPG", "DOH", "FPH"], answer: "EPH" },
    { question: "Find the missing term: A, C, F, J, ?", options: ["M", "N", "O", "P"], answer: "O" },
    { question: "Complete the pattern: 2, 5, 10, 17, 26, ?", options: ["35", "36", "37", "38"], answer: "37" },
    { question: "Find the next letter group: AZ, BY, CX, ?", options: ["DW", "DV", "EW", "DX"], answer: "DW" },
    { question: "Choose the analogy: Finger is to Hand as Toe is to:", options: ["Foot", "Leg", "Nail", "Ankle"], answer: "Foot" },
    { question: "Find the next number: 1, 4, 9, 16, ?", options: ["20", "24", "25", "36"], answer: "25" },
    { question: "What comes next: B, E, H, K, ?", options: ["L", "M", "N", "O"], answer: "N" },
    { question: "Find the next number: 81, 27, 9, 3, ?", options: ["1", "0", "2", "6"], answer: "1" },
  ],
  verbal: [
    { question: "Choose the synonym of 'Rapid'.", options: ["Slow", "Quick", "Calm", "Late"], answer: "Quick" },
    { question: "Choose the antonym of 'Expand'.", options: ["Stretch", "Increase", "Shrink", "Lengthen"], answer: "Shrink" },
    { question: "Fill in the blank: She ____ to the office every day.", options: ["go", "goes", "gone", "going"], answer: "goes" },
    { question: "Which sentence is grammatically correct?", options: ["He don't like tea.", "He doesn't likes tea.", "He doesn't like tea.", "He not like tea."], answer: "He doesn't like tea." },
    { question: "Choose the correctly spelled word.", options: ["Accomodate", "Acommodate", "Accommodate", "Acomodate"], answer: "Accommodate" },
    { question: "Fill in the blank: We have lived here ____ 2019.", options: ["for", "since", "from", "at"], answer: "since" },
    { question: "Choose the antonym of 'Ancient'.", options: ["Old", "Historic", "Modern", "Traditional"], answer: "Modern" },
    { question: "Choose the correct article: She bought ____ umbrella.", options: ["a", "an", "the", "no article"], answer: "an" },
    { question: "Pick the synonym of 'Accurate'.", options: ["Exact", "Random", "Weak", "Harsh"], answer: "Exact" },
    { question: "Choose the best meaning of 'Reluctant'.", options: ["Willing", "Uncertain", "Unwilling", "Excited"], answer: "Unwilling" },
  ],
};

function getSectionConfig(sectionId) {
  return SECTION_OPTIONS.find((section) => section.id === sectionId) || SECTION_OPTIONS[0];
}

function isCodingSection(sectionId) {
  return getSectionConfig(sectionId).mode === "coding";
}

function getConfiguredQuestionCount(sectionId, selectedCount) {
  if (isCodingSection(sectionId)) {
    return selectedCount;
  }
  return Math.max(selectedCount, 10);
}

function getConfiguredDuration(sectionId, selectedCount) {
  if (isCodingSection(sectionId)) return 0;
  return getConfiguredQuestionCount(sectionId, selectedCount) * 60;
}

function formatTime(totalSeconds) {
  const safeSeconds = Math.max(totalSeconds, 0);
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function shuffleArray(items) {
  const shuffled = [...items];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[randomIndex]] = [shuffled[randomIndex], shuffled[index]];
  }
  return shuffled;
}

function buildMcqQuestions(sectionId, count) {
  const bank = QUESTION_BANKS[sectionId] || [];
  if (!bank.length) return [];

  const questions = [];
  let round = 0;
  while (questions.length < count) {
    const currentRound = round;
    const batch = shuffleArray(bank).map((question, index) => ({
      ...question,
      sessionId: `${sectionId}-${currentRound}-${index}`,
    }));
    questions.push(...batch);
    round += 1;
  }
  return questions.slice(0, count);
}

function createSummary(sectionId, questions, answers, reason = "manual") {
  const answeredCount = answers.filter((answer) => (answer || "").trim().length > 0).length;
  const score = questions.filter((question, index) => answers[index] === question.answer).length;
  return {
    sectionId,
    mode: "mcq",
    totalQuestions: questions.length,
    answeredCount,
    score,
    autoSubmitted: reason === "auto",
    items: questions.map((question, index) => ({
      ...question,
      selectedAnswer: answers[index] || "Not answered",
      correctAnswer: question.answer,
      isCorrect: answers[index] === question.answer,
    })),
  };
}

function createCodingSessionSummary(sectionId, challenges, answers, language, runResults, submitResults, reason = "manual") {
  const items = (challenges || []).map((challenge, index) => {
    const execution = submitResults[index]?.execution || runResults[index] || { passed: 0, total: 0, results: [], status: "not_run" };
    return {
      challenge,
      sourceCode: answers[index] || "",
      execution,
      review: submitResults[index]?.review || null,
      language,
    };
  });
  return {
    sectionId,
    mode: "coding",
    totalQuestions: items.length,
    answeredCount: items.filter((item) => item.sourceCode.trim()).length,
    score: items.reduce((total, item) => total + (item.execution.passed || 0), 0),
    autoSubmitted: reason === "auto",
    codingItems: items,
  };
}

function getStarterCode(challenge, language) {
  return challenge?.starter_code?.[language] || challenge?.starter_code?.javascript || "";
}

function getCodingChallengeKey(challenge) {
  const title = String(challenge?.title || challenge?.question || "").trim().toLowerCase();
  const description = String(challenge?.description || challenge?.prompt || "").trim().toLowerCase();
  return title || description;
}

function loadSeenCodingQuestions() {
  try {
    const raw = window.localStorage.getItem(CODING_HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return typeof parsed === "object" && parsed ? parsed : {};
  } catch {
    return {};
  }
}

function saveSeenCodingQuestions(data) {
  window.localStorage.setItem(CODING_HISTORY_KEY, JSON.stringify(data));
}

function filterVisibleLanguages(languages = []) {
  return languages.filter((language) => !HIDDEN_LANGUAGE_IDS.has(language.id));
}

function loadCodingQuestionPool() {
  try {
    const raw = window.localStorage.getItem(CODING_POOL_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return typeof parsed === "object" && parsed ? parsed : {};
  } catch {
    return {};
  }
}

function saveCodingQuestionPool(data) {
  window.localStorage.setItem(CODING_POOL_KEY, JSON.stringify(data));
}

function dedupeCodingChallenges(challenges = [], excludedKeys = [], limit = Infinity) {
  const seen = new Set(excludedKeys);
  const unique = [];

  for (const challenge of challenges) {
    const key = getCodingChallengeKey(challenge);
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    unique.push(challenge);
    if (unique.length >= limit) {
      break;
    }
  }

  return unique;
}

function buildLocalCodingFallback(level, index) {
  const fallbackPools = {
    easy: [
      {
        title: "Count Vowels in a String",
        description: "Given a string, print the number of vowels present in it.",
        constraints: ["1 <= length <= 10^5", "Treat vowels case-insensitively"],
        hints: ["Scan once through the string.", "Check a, e, i, o, u only."],
        examples: [{ input: "education", output: "5", explanation: "The vowels are e, u, a, i, o." }],
        public_test_cases: [{ input: "hello", expected_output: "2" }, { input: "rhythm", expected_output: "0" }],
      },
      {
        title: "Sum of Digits",
        description: "Given a non-negative integer, print the sum of its digits.",
        constraints: ["0 <= n <= 10^18"],
        hints: ["Process the characters or repeatedly divide by 10."],
        examples: [{ input: "482", output: "14", explanation: "4 + 8 + 2 = 14." }],
        public_test_cases: [{ input: "12345", expected_output: "15" }, { input: "700", expected_output: "7" }],
      },
      {
        title: "Count Even Numbers",
        description: "Given a space-separated list of integers, print how many are even.",
        constraints: ["1 <= number of integers <= 10^5"],
        hints: ["Use modulo 2.", "You only need a counter."],
        examples: [{ input: "1 2 3 4 5 6", output: "3", explanation: "2, 4, and 6 are even." }],
        public_test_cases: [{ input: "10 15 20 25", expected_output: "2" }, { input: "7 9 11", expected_output: "0" }],
      },
      {
        title: "Count Positive Numbers",
        description: "Given a space-separated list of integers, print how many numbers are greater than zero.",
        constraints: ["1 <= number of integers <= 10^5"],
        hints: ["Split the input and count values above zero."],
        examples: [{ input: "-1 0 4 7 -3", output: "2", explanation: "Only 4 and 7 are positive." }],
        public_test_cases: [{ input: "1 2 3", expected_output: "3" }, { input: "-5 -2 0", expected_output: "0" }],
      },
      {
        title: "Largest Digit in a Number",
        description: "Given a non-negative integer, print the largest digit present in it.",
        constraints: ["0 <= n <= 10^18"],
        hints: ["Process the number as a string or digit by digit."],
        examples: [{ input: "48219", output: "9", explanation: "9 is the largest digit." }],
        public_test_cases: [{ input: "700", expected_output: "7" }, { input: "12345", expected_output: "5" }],
      },
      {
        title: "Reverse Each Word",
        description: "Given a sentence, reverse every word individually while preserving word order.",
        constraints: ["1 <= length of input <= 10^5"],
        hints: ["Split into words, reverse each word, then join."],
        examples: [{ input: "code daily", output: "edoc yliad", explanation: "Each word is reversed in place." }],
        public_test_cases: [{ input: "hello world", expected_output: "olleh dlrow" }, { input: "a bc def", expected_output: "a cb fed" }],
      },
      {
        title: "Second Largest Number",
        description: "Given a space-separated list of distinct integers, print the second largest value.",
        constraints: ["2 <= number of integers <= 10^5", "All values are distinct"],
        hints: ["Track the largest and second largest values while scanning."],
        examples: [{ input: "3 8 2 10 6", output: "8", explanation: "10 is largest, so 8 is second largest." }],
        public_test_cases: [{ input: "1 9", expected_output: "1" }, { input: "4 7 2 11 5", expected_output: "7" }],
      },
      {
        title: "Count Words With Vowels",
        description: "Given a line of text, print how many words contain at least one vowel.",
        constraints: ["1 <= number of words <= 10^5", "Treat vowels case-insensitively"],
        hints: ["Split by whitespace and check each word for vowels."],
        examples: [{ input: "sky apple dry orange", output: "2", explanation: "Only apple and orange contain vowels." }],
        public_test_cases: [{ input: "code gym fly", expected_output: "1" }, { input: "a e i", expected_output: "3" }],
      },
    ],
    medium: [
      {
        title: "Group Anagrams",
        description: "Given a list of words, group the anagrams and print the groups in deterministic order.",
        constraints: ["Use standard input and output."],
        hints: ["Use a sorted string as the group key."],
        examples: [{ input: "eat tea tan ate nat bat", output: "[[ate,eat,tea],[bat],[nat,tan]]", explanation: "Words with same sorted form are grouped." }],
        public_test_cases: [{ input: "abc bca cab foo oof", expected_output: "[[abc,bca,cab],[foo,oof]]" }],
      },
      {
        title: "Longest Consecutive Run",
        description: "Given a space-separated list of integers, print the length of the longest consecutive sequence.",
        constraints: ["Aim for near O(n) time."],
        hints: ["Use a set.", "Only start counting when a value has no predecessor."],
        examples: [{ input: "100 4 200 1 3 2", output: "4", explanation: "1,2,3,4 is the longest sequence." }],
        public_test_cases: [{ input: "9 1 4 7 3 2 6 8 0", expected_output: "5" }],
      },
      {
        title: "Product of Array Except Self",
        description: "Given a list of integers, print the product of array except self for each position.",
        constraints: ["Do not use division."],
        hints: ["Build prefix and suffix products."],
        examples: [{ input: "1 2 3 4", output: "24 12 8 6", explanation: "Each index gets the product of all other numbers." }],
        public_test_cases: [{ input: "2 3 4 5", expected_output: "60 40 30 24" }],
      },
      {
        title: "Top K Frequent Numbers",
        description: "Given a space-separated list of integers and a final integer k on the next line, print the k most frequent numbers in descending frequency order, breaking ties by smaller number first.",
        constraints: ["1 <= n <= 10^5", "1 <= k <= number of distinct values"],
        hints: ["Count frequencies with a hash map, then sort by frequency and value."],
        examples: [{ input: "1 1 1 2 2 3\n2", output: "1 2", explanation: "1 appears three times and 2 appears twice." }],
        public_test_cases: [{ input: "4 4 4 6 6 8\n2", expected_output: "4 6" }, { input: "5 5 1 1 2 2\n1", expected_output: "1" }],
      },
      {
        title: "Merge Overlapping Intervals",
        description: "Given intervals as lines of 'start end', merge all overlapping intervals and print the merged intervals in order.",
        constraints: ["1 <= number of intervals <= 10^5"],
        hints: ["Sort by start time, then merge while overlaps continue."],
        examples: [{ input: "1 3\n2 6\n8 10\n15 18", output: "1 6\n8 10\n15 18", explanation: "The first two intervals overlap and merge." }],
        public_test_cases: [{ input: "1 4\n4 5", expected_output: "1 5" }, { input: "1 2\n3 4", expected_output: "1 2\n3 4" }],
      },
      {
        title: "Longest Subarray With Sum K",
        description: "Given a space-separated list of integers and a target k on the next line, print the length of the longest contiguous subarray whose sum equals k.",
        constraints: ["1 <= n <= 10^5", "-10^9 <= values <= 10^9"],
        hints: ["Use prefix sums and store the earliest index for each prefix sum."],
        examples: [{ input: "1 -1 5 -2 3\n3", output: "4", explanation: "The subarray [1, -1, 5, -2] sums to 3." }],
        public_test_cases: [{ input: "-2 -1 2 1\n1", expected_output: "2" }, { input: "1 2 3 4 5\n9", expected_output: "3" }],
      },
      {
        title: "Validate Bracket Sequence",
        description: "Given a string containing only brackets (), {}, and [], print Valid if the sequence is balanced, otherwise print Invalid.",
        constraints: ["1 <= length <= 10^5"],
        hints: ["Use a stack and match each closing bracket with the latest opening bracket."],
        examples: [{ input: "{[()]}", output: "Valid", explanation: "All brackets close in the correct order." }],
        public_test_cases: [{ input: "([)]", expected_output: "Invalid" }, { input: "(()[])", expected_output: "Valid" }],
      },
      {
        title: "Spiral Order of Matrix",
        description: "Given a matrix where each line is a row of space-separated integers, print the elements in spiral order.",
        constraints: ["1 <= rows, cols <= 100"],
        hints: ["Track top, bottom, left, and right boundaries."],
        examples: [{ input: "1 2 3\n4 5 6\n7 8 9", output: "1 2 3 6 9 8 7 4 5", explanation: "Traverse layer by layer in spiral order." }],
        public_test_cases: [{ input: "1 2\n3 4", expected_output: "1 2 4 3" }, { input: "1 2 3 4", expected_output: "1 2 3 4" }],
      },
    ],
    hard: [
      {
        title: "Longest Unique Substring Length",
        description: "Given a string, print the length of the longest substring without repeating characters.",
        constraints: ["Aim for an O(n) sliding-window solution."],
        hints: ["Track last seen positions.", "Move the left pointer only forward."],
        examples: [{ input: "abcabcbb", output: "3", explanation: "abc is the longest unique substring." }],
        public_test_cases: [{ input: "pwwkew", expected_output: "3" }, { input: "bbbbb", expected_output: "1" }],
      },
      {
        title: "Minimum Window Substring Length",
        description: "Given strings s and t separated by a newline, print the length of the minimum window in s containing all characters of t.",
        constraints: ["Print 0 if no valid window exists."],
        hints: ["Use a sliding window with frequency maps."],
        examples: [{ input: "ADOBECODEBANC\nABC", output: "4", explanation: "BANC is the minimum valid window." }],
        public_test_cases: [{ input: "a\na", expected_output: "1" }, { input: "a\naa", expected_output: "0" }],
      },
      {
        title: "Largest Rectangle in Histogram",
        description: "Given histogram bar heights, print the area of the largest rectangle.",
        constraints: ["Aim for an O(n) stack solution."],
        hints: ["Use a monotonic increasing stack."],
        examples: [{ input: "2 1 5 6 2 3", output: "10", explanation: "The best rectangle spans heights 5 and 6." }],
        public_test_cases: [{ input: "2 4", expected_output: "4" }, { input: "6 2 5 4 5 1 6", expected_output: "12" }],
      },
      {
        title: "Sliding Window Maximum",
        description: "Given a space-separated list of integers and a window size k on the next line, print the maximum for each sliding window.",
        constraints: ["1 <= n <= 10^5", "Use an efficient approach better than O(nk)"],
        hints: ["Use a deque to keep candidate indices in decreasing order."],
        examples: [{ input: "1 3 -1 -3 5 3 6 7\n3", output: "3 3 5 5 6 7", explanation: "Each output is the max of its window." }],
        public_test_cases: [{ input: "9 10 9 -7 -4 -8 2 -6\n5", expected_output: "10 10 9 2" }, { input: "1\n1", expected_output: "1" }],
      },
      {
        title: "Trapping Rain Water",
        description: "Given space-separated bar heights, print the total units of water trapped after raining.",
        constraints: ["1 <= number of bars <= 2 * 10^5"],
        hints: ["Use two pointers or prefix and suffix maximum arrays."],
        examples: [{ input: "0 1 0 2 1 0 1 3 2 1 2 1", output: "6", explanation: "The histogram traps 6 units of water." }],
        public_test_cases: [{ input: "4 2 0 3 2 5", expected_output: "9" }, { input: "1 2 3 4", expected_output: "0" }],
      },
      {
        title: "Median of Running Stream",
        description: "Given a stream of integers as a space-separated list, print the median after each insertion.",
        constraints: ["1 <= n <= 10^5"],
        hints: ["Maintain two heaps and balance them after each insertion."],
        examples: [{ input: "5 15 1 3", output: "5 10 5 4", explanation: "The running medians are 5, 10, 5, and 4." }],
        public_test_cases: [{ input: "2 4 6", expected_output: "2 3 4" }, { input: "1 1 1", expected_output: "1 1 1" }],
      },
      {
        title: "Word Ladder Steps",
        description: "Given a begin word, end word, and a dictionary of lowercase words on separate lines, print the minimum number of transformations needed to reach the end word, changing one letter at a time. Print 0 if impossible.",
        constraints: ["All words have the same length.", "1 <= dictionary size <= 5000"],
        hints: ["Breadth-first search works well.", "Generate one-letter transformations efficiently."],
        examples: [{ input: "hit\ncog\nhot dot dog lot log cog", output: "5", explanation: "One shortest path is hit -> hot -> dot -> dog -> cog." }],
        public_test_cases: [{ input: "hit\ncog\nhot dot dog lot log cog", expected_output: "5" }, { input: "hit\ncog\nhot dot dog lot log", expected_output: "0" }],
      },
      {
        title: "Alien Dictionary Order",
        description: "Given sorted dictionary words from an alien language, print one valid character order. Print Invalid if no order exists.",
        constraints: ["1 <= number of words <= 10^4"],
        hints: ["Build a graph from the first differing character between adjacent words, then use topological sorting."],
        examples: [{ input: "baa abcd abca cab cad", output: "bdac", explanation: "bdac is one valid topological ordering." }],
        public_test_cases: [{ input: "caa aaa aab", expected_output: "cab" }, { input: "abc ab", expected_output: "Invalid" }],
      },
    ],
  };

  const pool = fallbackPools[level] || fallbackPools.easy;
  const base = pool[index % pool.length];
  return {
    ...base,
    id: `frontend-${level}-${index + 1}`,
    difficulty: level,
    sessionId: `coding-challenge-${index + 1}`,
    type: "coding",
    question: base.title,
    prompt: base.description,
    starter_code: {
      javascript: `// ${base.title}\nconst fs = require("fs");\nconst input = fs.readFileSync(0, "utf8").trim();\n\nfunction solve(rawInput) {\n  // Write your solution here\n  return "";\n}\n\nprocess.stdout.write(String(solve(input)).trim());\n`,
      java: `import java.io.*;\n\npublic class Solution {\n    static String solve(String input) {\n        // Write your solution here\n        return "";\n    }\n\n    public static void main(String[] args) throws Exception {\n        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n        StringBuilder sb = new StringBuilder();\n        String line;\n        boolean first = true;\n        while ((line = br.readLine()) != null) {\n            if (!first) sb.append("\\n");\n            sb.append(line);\n            first = false;\n        }\n        System.out.print(solve(sb.toString().trim()).trim());\n    }\n}\n`,
      python: `# ${base.title}\nimport sys\n\n\ndef solve(raw_input: str) -> str:\n    # Write your solution here\n    return ""\n\n\nif __name__ == "__main__":\n    print(str(solve(sys.stdin.read().strip())).strip())\n`,
    },
  };
}

function buildLocalCodingSession(level, count, excludedKeys = []) {
  const excluded = new Set(excludedKeys);
  const items = [];
  let index = 0;
  let attempts = 0;
  while (items.length < count && attempts < count * 10) {
    const challenge = buildLocalCodingFallback(level, index);
    const key = getCodingChallengeKey(challenge);
    if (!excluded.has(key)) {
      excluded.add(key);
      items.push(challenge);
    }
    index += 1;
    attempts += 1;
  }
  return items;
}

function buildGuaranteedCodingSession(level, count, excludedKeys = []) {
  const uniqueItems = buildLocalCodingSession(level, count, excludedKeys);
  if (uniqueItems.length >= count) {
    return uniqueItems;
  }

  const filledItems = [...uniqueItems];
  let index = 0;
  while (filledItems.length < count) {
    filledItems.push(buildLocalCodingFallback(level, index));
    index += 1;
  }
  return filledItems;
}

function normalizeCodingChallenge(rawChallenge, index) {
  return {
    ...rawChallenge,
    sessionId: `coding-challenge-${index + 1}`,
    type: "coding",
    question: rawChallenge.title || `Coding Question ${index + 1}`,
    prompt: rawChallenge.description || "",
  };
}

async function fetchUniqueCodingChallenges(level, desiredCount, excludedKeys = []) {
  const uniqueChallenges = [];
  const seenChallengeKeys = new Set((excludedKeys || []).filter(Boolean));
  let attempts = 0;
  const maxAttempts = Math.max(desiredCount * 4, 12);

  while (uniqueChallenges.length < desiredCount && attempts < maxAttempts) {
    const remaining = desiredCount - uniqueChallenges.length;
    const batchSize = Math.min(Math.max(remaining, 2), 4);
    attempts += batchSize;

    const responses = await Promise.all(
      Array.from({ length: batchSize }, () =>
        axios.post(`${API_BASE_URL}/coding/challenge`, {
          difficulty: level,
          excluded_questions: Array.from(seenChallengeKeys),
        }).catch(() => null)
      )
    );

    responses.forEach((response) => {
      const rawChallenge = response?.data?.challenge;
      if (!rawChallenge || uniqueChallenges.length >= desiredCount) {
        return;
      }

      const normalizedChallenge = normalizeCodingChallenge(rawChallenge, uniqueChallenges.length);
      const challengeKey = getCodingChallengeKey(normalizedChallenge);
      if (!challengeKey || seenChallengeKeys.has(challengeKey)) {
        return;
      }

      seenChallengeKeys.add(challengeKey);
      uniqueChallenges.push(normalizedChallenge);
    });
  }

  return {
    challenges: uniqueChallenges,
    seenKeys: Array.from(seenChallengeKeys),
  };
}

function AptitudeTest() {
  const [stage, setStage] = useState("landing");
  const [selectedSection, setSelectedSection] = useState("aptitude");
  const [questionCount, setQuestionCount] = useState(10);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [timeLeft, setTimeLeft] = useState(0);
  const [summary, setSummary] = useState(null);
  const [runtimeLanguages, setRuntimeLanguages] = useState([]);
  const [codingLevel, setCodingLevel] = useState("easy");
  const [codingLanguage, setCodingLanguage] = useState("");
  const [codingRunResults, setCodingRunResults] = useState([]);
  const [codingRunSources, setCodingRunSources] = useState([]);
  const [codingSubmitResults, setCodingSubmitResults] = useState([]);
  const [, setCodingLoading] = useState(false);
  const [codingRunLoading, setCodingRunLoading] = useState(false);
  const [codingSubmitLoading, setCodingSubmitLoading] = useState(false);
  const [codingError, setCodingError] = useState("");
  const [codingTimerStarted, setCodingTimerStarted] = useState(false);
  const [startingTest, setStartingTest] = useState(false);
  const setupSectionRef = useRef(null);

  const selectedSectionConfig = useMemo(() => getSectionConfig(selectedSection), [selectedSection]);
  const codingMode = selectedSectionConfig.mode === "coding";
  const configuredQuestionCount = getConfiguredQuestionCount(selectedSection, questionCount);
  const configuredDuration = codingMode
    ? configuredQuestionCount * ((CODING_LEVELS.find((level) => level.id === codingLevel)?.timerMinutes || 10) * 60)
    : getConfiguredDuration(selectedSection, questionCount);
  const totalMinutes = Math.floor(configuredDuration / 60);
  const currentQuestion = questions[currentIndex];
  const answeredCount = answers.filter((answer) => (answer || "").trim().length > 0).length;
  const minQuestionCount = codingMode ? 5 : 10;
  const sliderMaxQuestionCount = codingMode ? 20 : 50;
  const isOverviewStage = stage === "landing" || stage === "setup";
  const selectedRuntime = useMemo(() => runtimeLanguages.find((item) => item.id === codingLanguage) || null, [runtimeLanguages, codingLanguage]);
  const currentCodingRunResult = codingRunResults[currentIndex] || null;
  const isCodingBusy = codingRunLoading || codingSubmitLoading;
  const hasSelectedCodingLanguage = Boolean(codingLanguage);

  useEffect(() => {
    let ignore = false;
    const loadRuntimeStatus = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/coding/runtime-status`);
        if (ignore) return;
        const fallback = [
          { id: "javascript", label: "JavaScript (Node.js)", available: true },
          { id: "java", label: "Java", available: true },
          { id: "python", label: "Python", available: false },
          { id: "c", label: "C", available: false },
          { id: "cpp", label: "C++", available: false },
          { id: "csharp", label: "C#", available: false },
          { id: "typescript", label: "TypeScript", available: false },
        ];
        const languages = Array.isArray(response.data?.languages) && response.data.languages.length ? response.data.languages : fallback;
        const visibleLanguages = filterVisibleLanguages(languages);
        setRuntimeLanguages(visibleLanguages);
        setCodingLanguage((current) => (visibleLanguages.some((item) => item.id === current) ? current : ""));
      } catch {
        if (!ignore) {
          setRuntimeLanguages(filterVisibleLanguages([
            { id: "javascript", label: "JavaScript (Node.js)", available: true },
            { id: "java", label: "Java", available: true },
            { id: "python", label: "Python", available: false },
            { id: "c", label: "C", available: false },
            { id: "cpp", label: "C++", available: false },
          ]));
          setCodingLanguage("");
        }
      }
    };
    loadRuntimeStatus();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (codingMode) return;
    setQuestionCount((current) => Math.max(current, 10));
  }, [codingMode, selectedSection]);

  useEffect(() => {
    if (!codingMode || !currentQuestion || !codingLanguage) return;
    setAnswers((currentAnswers) => {
      if ((currentAnswers[currentIndex] || "").trim()) {
        return currentAnswers;
      }
      const nextAnswers = [...currentAnswers];
      nextAnswers[currentIndex] = getStarterCode(currentQuestion, codingLanguage);
      return nextAnswers;
    });
  }, [codingLanguage, codingMode, currentIndex, currentQuestion]);

  useEffect(() => {
    if (stage !== "test" || !codingMode || !currentQuestion || codingTimerStarted) return;
    setTimeLeft(configuredDuration);
    setCodingTimerStarted(true);
  }, [codingMode, codingTimerStarted, configuredDuration, currentQuestion, stage]);

  useEffect(() => {
    if (stage !== "test") return undefined;
    if (codingMode && (!codingTimerStarted || !currentQuestion)) return undefined;
    if (timeLeft <= 0) {
      if (codingMode && (answers[currentIndex] || "").trim()) {
        void handleSubmitCode("auto");
      } else if (!codingMode) {
        setStage("summary");
        setSummary(createSummary(selectedSection, questions, answers, "auto"));
        window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
      }
      return undefined;
    }
    const timer = window.setInterval(() => {
      setTimeLeft((currentTime) => currentTime - 1);
    }, 1000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answers, codingMode, questions, selectedSection, stage, timeLeft, currentIndex]);

  function scrollToSetupSection() {
    window.requestAnimationFrame(() => {
      setupSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function handleOpenSetup() {
    if (startingTest) return;
    setStage("setup");
    setQuestions([]);
    setAnswers([]);
    setCurrentIndex(0);
    setSummary(null);
    setTimeLeft(0);
    setCodingRunResults([]);
    setCodingRunSources([]);
    setCodingSubmitResults([]);
    setCodingRunLoading(false);
    setCodingSubmitLoading(false);
    setCodingError("");
    setCodingTimerStarted(false);
    scrollToSetupSection();
  }

  async function handleStartTest() {
    if (startingTest) return;
    setStartingTest(true);

    if (codingMode) {
      const seenHistory = loadSeenCodingQuestions();
      const seenForLevel = Array.isArray(seenHistory[codingLevel]) ? seenHistory[codingLevel] : [];
      const questionPool = loadCodingQuestionPool();
      const poolForLevel = Array.isArray(questionPool[codingLevel]) ? questionPool[codingLevel] : [];
      const pooledChallenges = dedupeCodingChallenges(poolForLevel, seenForLevel, configuredQuestionCount);
      const fallbackChallenges = buildGuaranteedCodingSession(
        codingLevel,
        configuredQuestionCount - pooledChallenges.length,
        [...seenForLevel, ...pooledChallenges.map((challenge) => getCodingChallengeKey(challenge))],
      );
      const initialChallenges = [...pooledChallenges, ...fallbackChallenges];
      const remainingPool = poolForLevel.filter((challenge) => {
        const key = getCodingChallengeKey(challenge);
        return key && !initialChallenges.some((item) => getCodingChallengeKey(item) === key);
      });

      setQuestions(initialChallenges);
      setAnswers(new Array(initialChallenges.length).fill(""));
      setCodingRunResults(new Array(initialChallenges.length).fill(null));
      setCodingRunSources(new Array(initialChallenges.length).fill(""));
      setCodingSubmitResults(new Array(initialChallenges.length).fill(null));
      setCurrentIndex(0);
      setTimeLeft(0);
      setSummary(null);
      setCodingTimerStarted(false);
      setStage("test");
      window.scrollTo({ top: 0, left: 0, behavior: "smooth" });

      saveSeenCodingQuestions({
        ...seenHistory,
        [codingLevel]: [...seenForLevel, ...initialChallenges.map((challenge) => getCodingChallengeKey(challenge))].slice(-1000),
      });
      saveCodingQuestionPool({
        ...questionPool,
        [codingLevel]: remainingPool.slice(-60),
      });

      setStartingTest(false);
      setCodingLoading(true);
      setCodingError("");

      void (async () => {
        try {
          const aiSeedExclusions = [
            ...seenForLevel,
            ...initialChallenges.map((challenge) => getCodingChallengeKey(challenge)),
            ...remainingPool.map((challenge) => getCodingChallengeKey(challenge)),
          ];
          const { challenges: aiChallenges } = await fetchUniqueCodingChallenges(
            codingLevel,
            configuredQuestionCount + 8,
            aiSeedExclusions,
          );

          if (!aiChallenges.length) {
            return;
          }

          const reserveChallenges = aiChallenges.slice(0, 60);
          saveCodingQuestionPool({
            ...questionPool,
            [codingLevel]: dedupeCodingChallenges([...remainingPool, ...reserveChallenges], seenForLevel, 60),
          });
        } catch (error) {
          setCodingError(error?.response?.data?.detail || "Coding test started with ready questions. Fresh AI questions are still warming up.");
        } finally {
          setCodingLoading(false);
        }
      })();
      return;
    }

    const sessionQuestions = buildMcqQuestions(selectedSection, configuredQuestionCount);
    setQuestions(sessionQuestions);
    setAnswers(new Array(sessionQuestions.length).fill(""));
    setCurrentIndex(0);
    setTimeLeft(configuredDuration);
    setSummary(null);
    setStage("test");
    setStartingTest(false);
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  }

  function handleSelectAnswer(value) {
    setAnswers((currentAnswers) => {
      const nextAnswers = [...currentAnswers];
      nextAnswers[currentIndex] = value;
      return nextAnswers;
    });
  }

  async function handleRunCode() {
    const sourceCode = answers[currentIndex] || "";
    if (!currentQuestion || !sourceCode.trim()) return;
    if (selectedRuntime?.available === false) {
      setCodingError(`${selectedRuntime.label} will be coming soon.`);
      setCodingRunResults((current) => {
        const next = [...current];
        next[currentIndex] = null;
        return next;
      });
      return;
    }
    setCodingRunLoading(true);
    setCodingError("");
    try {
      const response = await axios.post(`${API_BASE_URL}/coding/run`, {
        language: codingLanguage,
        source_code: sourceCode,
        test_cases: currentQuestion.public_test_cases || [],
      });
      setCodingRunResults((current) => {
        const next = [...current];
        next[currentIndex] = response.data;
        return next;
      });
      setCodingRunSources((current) => {
        const next = [...current];
        next[currentIndex] = sourceCode;
        return next;
      });
    } catch (error) {
      setCodingError(error?.response?.data?.detail || "Failed to run code.");
      setCodingRunResults((current) => {
        const next = [...current];
        next[currentIndex] = null;
        return next;
      });
      setCodingRunSources((current) => {
        const next = [...current];
        next[currentIndex] = "";
        return next;
      });
    } finally {
      setCodingRunLoading(false);
    }
  }

  async function handleSubmitCode(reason = "manual") {
    const sourceCode = answers[currentIndex] || "";
    if (!currentQuestion || !sourceCode.trim()) return;
    if (selectedRuntime?.available === false) {
      setCodingError(`${selectedRuntime.label} will be coming soon.`);
      setCodingSubmitResults((current) => {
        const next = [...current];
        next[currentIndex] = null;
        return next;
      });
      return;
    }
    setCodingSubmitLoading(true);
    setCodingError("");
    try {
      const cachedPublicExecution = codingRunSources[currentIndex] === sourceCode && codingRunResults[currentIndex]?.status === "ok"
        ? codingRunResults[currentIndex]
        : null;
      const response = await axios.post(`${API_BASE_URL}/coding/submit`, {
        language: codingLanguage,
        source_code: sourceCode,
        challenge: currentQuestion,
        fast_feedback: true,
        cached_public_execution: cachedPublicExecution,
      });
      setCodingSubmitResults((current) => {
        const next = [...current];
        next[currentIndex] = response.data;
        return next;
      });
      if (currentIndex === questions.length - 1) {
        setSummary(createCodingSessionSummary(selectedSection, questions, answers, codingLanguage, codingRunResults, [...codingSubmitResults.slice(0, currentIndex), response.data, ...codingSubmitResults.slice(currentIndex + 1)], reason));
        setStage("summary");
        window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
      } else {
        setCurrentIndex((current) => current + 1);
      }
    } catch (error) {
      setCodingError(error?.response?.data?.detail || "Failed to submit solution.");
    } finally {
      setCodingSubmitLoading(false);
    }
  }

  function handleFinishMcq(reason = "manual") {
    setStage("summary");
    setSummary(createSummary(selectedSection, questions, answers, reason));
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  }

  return (
    <div className="mock-page reveal">
      <MiniNavbar />

      <div className="mock-hero aptitude-hero" style={{ background: "linear-gradient(90deg, #0f766e 0%, #14b8a6 55%, #67e8f9 100%)" }}>
        <div>
          <h1>Aptitude Test</h1>
          <p>Choose a section, decide how many questions you want to practice, and take a timed round with instant summary review.</p>
          <button className="mock-btn" onClick={handleOpenSetup} disabled={startingTest}>Start Aptitude Test</button>
        </div>
        <img src={aptitudeHero} alt="Aptitude Test" className="mock-hero-img" />
      </div>

      {isOverviewStage && (
        <>
          <div className="mock-section">
            <div className="section-header-row" style={{ justifyContent: "flex-end", display: "none" }}>
              <button className="small-start-btn" onClick={handleOpenSetup} disabled={startingTest}>Start Aptitude</button>
            </div>
            <div className="aptitude-info-grid">
              <div className="aptitude-info-card aptitude-info-card-learn">
                <div className="aptitude-info-card-tag aptitude-info-card-tag-warm">What you'll learn</div>
                <ul>
                  <li>Quantitative, reasoning, and verbal problem solving with timed MCQ practice</li>
                  <li>Coding challenges with selectable level, multiple AI-generated questions, and runnable code</li>
                  <li>Passed test case counts and AI code review after submission</li>
                </ul>
              </div>
              <div className="aptitude-info-card aptitude-info-card-types">
                <div className="aptitude-info-card-tag aptitude-info-card-tag-strong">Question types</div>
                <ul>
                  <li>MCQ sections use 4-option questions with 60 seconds per question</li>
                  <li>The coding section uses a split problem/editor layout like coding platforms</li>
                  <li>The editor starts with a starter template, not a solved answer</li>
                </ul>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', marginTop: '22px' }}>
              <button className="small-start-btn" onClick={handleOpenSetup} disabled={startingTest}>Start Aptitude</button>
            </div>
          </div>

          <div className="mock-section" ref={setupSectionRef}>
            <div className="aptitude-flow-card">
              <div className="aptitude-flow-header">
                <div>
                  <span className="aptitude-chip">Test setup</span>
                  <h2>Select your aptitude topic</h2>
                </div>
                <div className="aptitude-timer-preview">
                  <span>Total time</span>
                  <strong>{totalMinutes} min</strong>
                  <small>{codingMode ? `${configuredQuestionCount} coding questions` : `${configuredQuestionCount} questions x 60 sec`}</small>
                </div>
              </div>

              <div className="aptitude-setup-grid">
                {SECTION_OPTIONS.map((section) => (
                  <button
                  key={section.id}
                  type="button"
                  className={`aptitude-section-card ${selectedSection === section.id ? "is-active" : ""}`}
                  disabled={startingTest}
                  onClick={() => setSelectedSection(section.id)}
                >
                    <strong>{section.title}</strong>
                    <span>{section.description}</span>
                  </button>
                ))}
              </div>

              {codingMode ? (
                <div className="aptitude-count-card">
                <div className="aptitude-count-copy">
                  <span className="aptitude-chip">Coding setup</span>
                  <h3>{codingLevel.charAt(0).toUpperCase() + codingLevel.slice(1)} level, {questionCount} questions</h3>
                  <div className="aptitude-tip-row">
                    <span
                      className="aptitude-tip-sign"
                      title="Choose a coding difficulty level, then set how many coding questions you want in this session from 5 to 20."
                      aria-label="Tip: Choose a coding difficulty level, then set how many coding questions you want in this session from 5 to 20."
                      tabIndex={0}
                    >
                      <Info size={16} strokeWidth={2.2} />
                    </span>
                    <p>Choose a coding difficulty level, then set how many coding questions you want in this session from 5 to 20.</p>
                  </div>
                </div>
                  <div className="aptitude-count-controls">
                    <select className="aptitude-language-select" value={codingLevel} onChange={(event) => setCodingLevel(event.target.value)} disabled={startingTest}>
                      {CODING_LEVELS.map((level) => (
                        <option key={level.id} value={level.id}>{level.title}</option>
                      ))}
                    </select>
                    <input
                      type="range"
                      min="5"
                      max="20"
                      value={questionCount}
                      disabled={startingTest}
                      onChange={(event) => setQuestionCount(Number(event.target.value))}
                    />
                    <div className="aptitude-count-stepper">
                      <button type="button" onClick={() => setQuestionCount((current) => Math.max(5, current - 1))} disabled={startingTest}>-</button>
                      <div>{questionCount}</div>
                      <button type="button" onClick={() => setQuestionCount((current) => Math.min(20, current + 1))} disabled={startingTest}>+</button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="aptitude-count-card">
                  <div className="aptitude-count-copy">
                    <span className="aptitude-chip">Question count</span>
                    <h3>{questionCount} questions selected</h3>
                    <p>Choose between 10 and 50 questions for this section.</p>
                  </div>
                  <div className="aptitude-count-controls">
                    <input
                      type="range"
                      min={minQuestionCount}
                      max={sliderMaxQuestionCount}
                      value={questionCount}
                      disabled={startingTest}
                      onChange={(event) => {
                        const nextValue = Number(event.target.value);
                        setQuestionCount(Number.isNaN(nextValue) ? minQuestionCount : Math.max(minQuestionCount, nextValue));
                      }}
                    />
                    <div className="aptitude-count-stepper">
                      <button type="button" onClick={() => setQuestionCount((current) => Math.max(minQuestionCount, current - 1))} disabled={startingTest}>-</button>
                      <div>{questionCount}</div>
                      <button type="button" onClick={() => setQuestionCount((current) => current + 1)} disabled={startingTest}>+</button>
                    </div>
                  </div>
                </div>
              )}

              <div className="aptitude-flow-actions aptitude-setup-actions">
                <button
                  type="button"
                  className="small-start-btn aptitude-secondary-btn aptitude-setup-back-btn"
                  disabled={startingTest}
                  onClick={() => {
                    setStage("landing");
                    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
                  }}
                >
                  Back
                </button>
                <button
                  type="button"
                  className={`mock-btn aptitude-primary-btn ${startingTest ? "is-loading" : ""}`}
                  onClick={handleStartTest}
                  disabled={startingTest}
                  aria-busy={startingTest}
                >
                  {startingTest ? (
                    <>
                      <span className="aptitude-btn-spinner" aria-hidden="true" />
                      Starting Test...
                    </>
                  ) : (
                    "Start Test"
                  )}
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      {stage === "test" && currentQuestion && (
        <div className="mock-section">
          <div className="aptitude-test-shell">
            <div className="aptitude-test-topbar">
              <div>
                <span className="aptitude-chip">Live test</span>
                <h2>{selectedSectionConfig.title}</h2>
              </div>
              <div className="aptitude-timer-live">
                <span>Time left</span>
                <strong>{formatTime(timeLeft)}</strong>
                <small>{answeredCount}/{questions.length} answered</small>
              </div>
            </div>

            <div className="aptitude-progress-row">
              <div className="aptitude-progress-text">Question {currentIndex + 1} of {questions.length}</div>
              <div className="aptitude-progress-bar">
                <span style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }} />
              </div>
            </div>

            <div className="aptitude-question-card">
              <div className="aptitude-question-meta">
                {codingMode ? (
                  <>
                    <span>{CODING_LEVELS.find((level) => level.id === codingLevel)?.timerMinutes || 10} minute coding level timer</span>
                    <span>Question {currentIndex + 1} of {questions.length}: run code, then submit to move to the next coding question</span>
                  </>
                ) : (
                  <>
                    <span>60 sec per question</span>
                    <span>Total timer is running continuously</span>
                  </>
                )}
              </div>
              <h3>{currentQuestion.question}</h3>

              {codingMode ? (
                <div className="aptitude-code-workspace">
                  <div className="aptitude-code-panel">
                    <div className="aptitude-code-panel-header">
                      <span className="aptitude-chip">Problem</span>
                      <strong>{currentQuestion.difficulty || codingLevel}</strong>
                    </div>
                    <p className="aptitude-code-prompt">{currentQuestion.description || currentQuestion.prompt}</p>

                    {!!currentQuestion.constraints?.length && (
                      <div className="aptitude-code-block">
                        <h4>Constraints</h4>
                        <ul>
                          {currentQuestion.constraints.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {!!currentQuestion.hints?.length && (
                      <div className="aptitude-code-block">
                        <h4>Hints</h4>
                        <ul>
                          {currentQuestion.hints.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="aptitude-code-block">
                      <h4>Examples</h4>
                      <div className="aptitude-code-examples">
                        {(currentQuestion.examples || []).map((example, index) => (
                          <div key={`example-${index}`} className="aptitude-code-example">
                            <div><strong>Input:</strong> {example.input || "N/A"}</div>
                            <div><strong>Output:</strong> {example.output || "N/A"}</div>
                            {example.explanation ? <div><strong>Why:</strong> {example.explanation}</div> : null}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="aptitude-code-block">
                      <h4>Public Test Cases</h4>
                      <div className="aptitude-code-examples">
                        {(currentQuestion.public_test_cases || []).map((testCase, index) => (
                          <div key={`public-${index}`} className="aptitude-code-example">
                            <div><strong>Input:</strong> {testCase.input}</div>
                            <div><strong>Expected:</strong> {testCase.expected_output}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="aptitude-editor-panel">
                    <div className="aptitude-editor-toolbar">
                      <div>
                        <span className="aptitude-chip">Editor</span>
                      </div>
                      <select
                        className="aptitude-language-select"
                        value={codingLanguage}
                        onChange={(event) => {
                          const nextLanguage = event.target.value;
                          setCodingLanguage(nextLanguage);
                          setAnswers((currentAnswers) => {
                            const nextAnswers = [...currentAnswers];
                            nextAnswers[currentIndex] = nextLanguage ? getStarterCode(currentQuestion, nextLanguage) : "";
                            return nextAnswers;
                          });
                          setCodingRunResults((current) => {
                            const next = [...current];
                            next[currentIndex] = null;
                            return next;
                          });
                          setCodingSubmitResults((current) => {
                            const next = [...current];
                            next[currentIndex] = null;
                            return next;
                          });
                          setCodingError("");
                        }}
                      >
                        <option value="">Select language</option>
                        {runtimeLanguages.map((language) => (
                          <option key={language.id} value={language.id}>
                            {language.available === false ? `${language.label} (Coming soon)` : language.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {selectedRuntime?.available === false ? (
                      <div className="aptitude-code-error">
                        {selectedRuntime.label} will be coming soon.
                      </div>
                    ) : null}

                    <label className="aptitude-code-answer" htmlFor="coding-response">
                      <span>Code Editor</span>
                      {hasSelectedCodingLanguage ? (
                        <textarea
                          id="coding-response"
                          value={answers[currentIndex] || ""}
                          onChange={(event) => handleSelectAnswer(event.target.value)}
                          placeholder={`Complete the main logic in ${selectedRuntime?.label || "your selected language"}...`}
                          className="aptitude-code-editor"
                        />
                      ) : (
                        <div
                          className="aptitude-code-editor"
                          style={{
                            background: "#0f172a",
                            color: "#e2e8f0",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            textAlign: "center",
                            padding: "32px",
                            whiteSpace: "pre-line",
                          }}
                        >
                          <div>
                            <div style={{ fontSize: "1.35rem", fontWeight: 800, marginBottom: "10px", color: "#f8fafc" }}>
                              Start your coding journey
                            </div>
                            <div style={{ color: "#94a3b8", lineHeight: 1.7 }}>
                              Choose a language to load the starter template,
                              then begin solving the challenge with confidence.
                            </div>
                          </div>
                        </div>
                      )}
                    </label>

                    <div className="aptitude-flow-actions aptitude-coding-actions">
                      <button
                        type="button"
                        className="small-start-btn aptitude-secondary-btn"
                        disabled={isCodingBusy || !hasSelectedCodingLanguage}
                        onClick={() => {
                          setAnswers((currentAnswers) => {
                            const nextAnswers = [...currentAnswers];
                            nextAnswers[currentIndex] = getStarterCode(currentQuestion, codingLanguage);
                            return nextAnswers;
                          });
                          setCodingRunResults((current) => {
                            const next = [...current];
                            next[currentIndex] = null;
                            return next;
                          });
                          setCodingSubmitResults((current) => {
                            const next = [...current];
                            next[currentIndex] = null;
                            return next;
                          });
                          setCodingError("");
                        }}
                      >
                        Reset Template
                      </button>
                      <button type="button" className="small-start-btn aptitude-secondary-btn" onClick={handleRunCode} disabled={isCodingBusy || !hasSelectedCodingLanguage || !(answers[currentIndex] || "").trim() || selectedRuntime?.available === false}>
                        {codingRunLoading ? "Running..." : "Run Code"}
                      </button>
                      <button type="button" className="mock-btn aptitude-primary-btn" onClick={() => handleSubmitCode("manual")} disabled={isCodingBusy || !hasSelectedCodingLanguage || !(answers[currentIndex] || "").trim() || selectedRuntime?.available === false}>
                        {codingSubmitLoading ? "Submitting..." : "Submit Solution"}
                      </button>
                    </div>

                    {codingError ? <div className="aptitude-code-error">{codingError}</div> : null}

                    {currentCodingRunResult ? (
                      <div className="aptitude-code-results">
                        <div className="aptitude-code-results-header">
                          <strong>Run Result</strong>
                          <span>{currentCodingRunResult.passed}/{currentCodingRunResult.total} public tests passed</span>
                        </div>
                        {(currentCodingRunResult.results || []).map((result) => (
                          <div key={`run-${result.index}`} className={`aptitude-code-result-card ${result.passed ? "is-pass" : "is-fail"}`}>
                            <strong>Test Case {result.index}</strong>
                            <div>Input: {result.input || "N/A"}</div>
                            <div>Expected: {result.expected_output || "N/A"}</div>
                            <div>Actual: {result.actual_output || "N/A"}</div>
                            {result.stderr ? <div>Error: {result.stderr}</div> : null}
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : (
                <div className="aptitude-options-grid">
                  {currentQuestion.options.map((option) => (
                    <button key={option} type="button" className={`aptitude-option ${answers[currentIndex] === option ? "is-selected" : ""}`} onClick={() => handleSelectAnswer(option)}>
                      {option}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {!codingMode && (
              <>
                <div className="aptitude-question-map">
                  {questions.map((question, index) => (
                    <button key={question.sessionId} type="button" className={`aptitude-map-dot ${index === currentIndex ? "is-current" : ""} ${answers[index] ? "is-answered" : ""}`} onClick={() => setCurrentIndex(index)}>
                      {index + 1}
                    </button>
                  ))}
                </div>

                <div className="aptitude-flow-actions">
                  <button type="button" className="small-start-btn aptitude-secondary-btn" onClick={() => setCurrentIndex((current) => Math.max(0, current - 1))} disabled={currentIndex === 0}>Previous</button>
                  <div className="aptitude-inline-actions">
                    <button type="button" className="small-start-btn aptitude-secondary-btn" onClick={() => handleFinishMcq("manual")}>Submit Now</button>
                    <button type="button" className="mock-btn aptitude-primary-btn" onClick={() => setCurrentIndex((current) => Math.min(questions.length - 1, current + 1))} disabled={currentIndex === questions.length - 1}>Next Question</button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {stage === "summary" && summary && (
        <div className="mock-section">
          <div className="aptitude-flow-card aptitude-summary-shell">
            <div className="aptitude-summary-hero">
              <div>
                <span className="aptitude-chip">Summary</span>
                <h2>{summary.autoSubmitted ? "Time is over. Your test was auto-submitted." : "Your test summary is ready."}</h2>
                <p>{summary.mode === "coding" ? "Below is your coding submission, passed test cases, and AI analysis." : "Below is the answer review with your chosen option and the correct answer for every question."}</p>
              </div>
              <div className="aptitude-summary-score">
                <span>{summary.mode === "coding" ? "Passed" : "Score"}</span>
                <strong>{summary.score}/{summary.totalQuestions}</strong>
                <small>{summary.answeredCount} answered</small>
              </div>
            </div>

            {summary.mode === "coding" ? (
              <div className="aptitude-review-list">
                {(summary.codingItems || []).map((item, index) => (
                  <article key={`coding-summary-${index}`} className="aptitude-review-card is-coding">
                    <div className="aptitude-review-top">
                      <span>Coding Question {index + 1}</span>
                      <strong>{item.execution?.passed || 0}/{item.execution?.total || 0} tests passed</strong>
                    </div>
                    <h3>{item.challenge?.title}</h3>
                    <p className="aptitude-review-prompt">{item.challenge?.description}</p>
                    <div className="aptitude-review-answer-grid">
                      <div>
                        <span>Language</span>
                        <p>{item.language || "N/A"}</p>
                      </div>
                      <div>
                        <span>AI review</span>
                        <p>{item.review?.summary || "No AI review available."}</p>
                      </div>
                    </div>
                    <div className="aptitude-code-results">
                      <div className="aptitude-code-results-header">
                        <strong>Test Case Results</strong>
                        <span>{item.execution?.passed || 0}/{item.execution?.total || 0}</span>
                      </div>
                      {(item.execution?.results || []).map((result) => (
                        <div key={`summary-${index}-${result.index}`} className={`aptitude-code-result-card ${result.passed ? "is-pass" : "is-fail"}`}>
                          <strong>Test Case {result.index}</strong>
                          <div>Input: {result.input || "N/A"}</div>
                          <div>Expected: {result.expected_output || "N/A"}</div>
                          <div>Actual: {result.actual_output || "N/A"}</div>
                          {result.stderr ? <div>Error: {result.stderr}</div> : null}
                        </div>
                      ))}
                    </div>
                    <div className="aptitude-review-answer-grid">
                      <div>
                        <span>Your code</span>
                        <p className="aptitude-code-summary-text">{item.sourceCode || "No code submitted."}</p>
                      </div>
                      <div>
                        <span>Improvement suggestions</span>
                        <p className="aptitude-code-summary-text">{(item.review?.next_steps || []).join(" | ") || "No suggestions available."}</p>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <>
                <div className="aptitude-summary-grid">
                  <div className="aptitude-summary-stat">
                    <span>Section</span>
                    <strong>{getSectionConfig(summary.sectionId).title}</strong>
                  </div>
                  <div className="aptitude-summary-stat">
                    <span>Total questions</span>
                    <strong>{summary.totalQuestions}</strong>
                  </div>
                  <div className="aptitude-summary-stat">
                    <span>Correct answers</span>
                    <strong>{summary.score}</strong>
                  </div>
                  <div className="aptitude-summary-stat">
                    <span>Not answered</span>
                    <strong>{summary.totalQuestions - summary.answeredCount}</strong>
                  </div>
                </div>
                <div className="aptitude-review-list">
                  {summary.items.map((item, index) => (
                    <article key={item.sessionId} className={`aptitude-review-card ${item.isCorrect ? "is-correct" : "is-incorrect"}`}>
                      <div className="aptitude-review-top">
                        <span>Question {index + 1}</span>
                        <strong>{item.isCorrect ? "Correct" : "Review needed"}</strong>
                      </div>
                      <h3>{item.question}</h3>
                      <div className="aptitude-review-answer-grid">
                        <div>
                          <span>Your answer</span>
                          <p>{item.selectedAnswer}</p>
                        </div>
                        <div>
                          <span>Correct answer</span>
                          <p>{item.correctAnswer}</p>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </>
            )}

            <div className="aptitude-flow-actions">
              <button type="button" className="small-start-btn aptitude-secondary-btn" onClick={handleOpenSetup}>Practice Again</button>
              <button type="button" className="mock-btn aptitude-primary-btn" onClick={() => setStage("landing")}>Back to Overview</button>
            </div>
          </div>
        </div>
      )}

      <div className="bottom-footer">Prepared by AI Powered Interview System</div>
    </div>
  );
}

export default AptitudeTest;

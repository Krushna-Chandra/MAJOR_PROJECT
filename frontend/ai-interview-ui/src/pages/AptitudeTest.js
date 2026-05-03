import React, { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { Info, MonitorUp, ShieldAlert, PhoneOff, Calculator, UserCircle2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import "../App.css";
import MiniNavbar from "../components/MiniNavbar";
import aptitudeHero from "../assets/aptitude.png";
import logo from "../assets/Website Logo.png";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";
const CODING_HISTORY_KEY = "apis-coding-question-history";
const CODING_POOL_KEY = "apis-coding-question-pool";
const APTITUDE_EXAM_SESSION_KEY = "apis-aptitude-exam-session";
const HIDDEN_LANGUAGE_IDS = new Set(["go", "rust", "php", "ruby", "kotlin", "swift"]);
const APTITUDE_STARTUP_MESSAGES = [
  "Generating questions...",
  "Organizing section-wise timers...",
  "Preparing your exam workspace...",
  "Finalizing instructions and navigation...",
];

const SECTION_OPTIONS = [
  { id: "aptitude-mock", title: "Aptitude Mock", mode: "mock", description: "A real-world mixed aptitude round with timed sections across fundamentals, quant, reasoning, verbal, and coding." },
  { id: "aptitude", title: "Aptitude", mode: "mcq", description: "Quantitative practice with arithmetic, percentage, ratio, averages, and data questions." },
  { id: "advanced-quant", title: "Advanced Quantitative Ability", mode: "mcq", description: "Intermediate-to-hard quantitative aptitude with tougher arithmetic, DI, probability, and problem-solving questions." },
  { id: "reasoning", title: "Reasoning", mode: "mcq", description: "Series, coding-decoding, analogy, arrangement, and logic-based questions." },
  { id: "verbal", title: "Qualitative / Verbal", mode: "mcq", description: "Vocabulary, grammar, fill-in-the-blanks, punctuation, and comprehension practice." },
  { id: "computer-fundamentals", title: "Computer Fundamentals", mode: "mcq", description: "Easy-to-moderate MCQs from DBMS, OS, CN, OOP, data structures, algorithms, and core CS basics." },
  { id: "coding", title: "Coding", mode: "coding", description: "Choose a coding level and solve multiple AI-generated coding questions in a platform-style editor." },
];

const CODING_LEVELS = [
  { id: "basic", title: "Basic", timerMinutes: 10, description: "Beginner-friendly DSA problems with straightforward logic and basic optimization." },
  { id: "advanced", title: "Advanced", timerMinutes: 14, description: "A mixed medium-to-hard coding track with stronger edge cases, optimization, and interview-style problem solving." },
  { id: "mixed", title: "Basic + Advanced", timerMinutes: 12, description: "A blended coding track that includes both beginner-friendly and advanced interview-style problems." },
];

const APTITUDE_MOCK_COUNT_OPTIONS = [30, 60, 90, 120];

const APTITUDE_MOCK_SECTION_ORDER = [
  "computer-fundamentals",
  "aptitude",
  "reasoning",
  "verbal",
  "advanced-quant",
  "coding-basic",
  "coding-advanced",
];

const SETUP_SECTION_ORDER = [
  "aptitude-mock",
  "computer-fundamentals",
  "aptitude",
  "reasoning",
  "verbal",
  "advanced-quant",
  "coding",
];

const APTITUDE_MOCK_DISTRIBUTION = {
  30: {
    "computer-fundamentals": 5,
    aptitude: 8,
    reasoning: 7,
    verbal: 4,
    "advanced-quant": 4,
    "coding-basic": 1,
    "coding-advanced": 1,
  },
  60: {
    "computer-fundamentals": 11,
    aptitude: 17,
    reasoning: 14,
    verbal: 8,
    "advanced-quant": 8,
    "coding-basic": 1,
    "coding-advanced": 1,
  },
  90: {
    "computer-fundamentals": 17,
    aptitude: 26,
    reasoning: 21,
    verbal: 12,
    "advanced-quant": 12,
    "coding-basic": 1,
    "coding-advanced": 1,
  },
  120: {
    "computer-fundamentals": 23,
    aptitude: 35,
    reasoning: 28,
    verbal: 16,
    "advanced-quant": 16,
    "coding-basic": 1,
    "coding-advanced": 1,
  },
};

const QUESTION_BANKS = {
  reasoning: [
  ],
  verbal: [
  ],
};

function getSectionConfig(sectionId) {
  return SECTION_OPTIONS.find((section) => section.id === sectionId) || SECTION_OPTIONS[0];
}

function getAptitudeMockSectionMeta(sectionId) {
  const sectionMap = {
    "computer-fundamentals": { id: "computer-fundamentals", title: "Computer Fundamentals", mode: "mcq" },
    aptitude: { id: "aptitude", title: "Aptitude", mode: "mcq" },
    reasoning: { id: "reasoning", title: "Reasoning", mode: "mcq" },
    verbal: { id: "verbal", title: "Verbal", mode: "mcq" },
    "advanced-quant": { id: "advanced-quant", title: "Advanced Quantitative Ability", mode: "mcq" },
    "coding-basic": { id: "coding-basic", title: "Coding Basic", mode: "coding", codingLevel: "basic" },
    "coding-advanced": { id: "coding-advanced", title: "Coding Advanced", mode: "coding", codingLevel: "advanced" },
  };
  return sectionMap[sectionId] || { id: sectionId, title: sectionId, mode: "mcq" };
}

function getOrderedSetupSections() {
  const orderIndex = new Map(SETUP_SECTION_ORDER.map((id, index) => [id, index]));
  return [...SECTION_OPTIONS].sort((a, b) => {
    const aIndex = orderIndex.has(a.id) ? orderIndex.get(a.id) : Number.MAX_SAFE_INTEGER;
    const bIndex = orderIndex.has(b.id) ? orderIndex.get(b.id) : Number.MAX_SAFE_INTEGER;
    return aIndex - bIndex;
  });
}

function getCodingLevelConfig(levelId) {
  return CODING_LEVELS.find((level) => level.id === levelId) || CODING_LEVELS[0];
}

function getCodingSourceLevels(levelId) {
  if (levelId === "advanced") {
    return ["medium", "hard"];
  }
  if (levelId === "mixed") {
    return ["easy", "medium", "hard"];
  }
  return ["easy"];
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

function getSecondsPerQuestion(sectionId) {
  if (sectionId === "computer-fundamentals") {
    return 30;
  }
  if (sectionId === "advanced-quant") {
    return 90;
  }
  return 60;
}

function isMockSection(sectionId) {
  return sectionId === "aptitude-mock";
}

function getMockTotalDuration(selectedCount) {
  const distribution = APTITUDE_MOCK_DISTRIBUTION[selectedCount] || APTITUDE_MOCK_DISTRIBUTION[30];
  return APTITUDE_MOCK_SECTION_ORDER.reduce((total, sectionId) => {
    const count = distribution[sectionId] || 0;
    if (sectionId === "coding-basic") {
      return total + (count * ((getCodingLevelConfig("basic").timerMinutes || 10) * 60));
    }
    if (sectionId === "coding-advanced") {
      return total + (count * ((getCodingLevelConfig("advanced").timerMinutes || 14) * 60));
    }
    return total + (count * getSecondsPerQuestion(sectionId));
  }, 0);
}

function getConfiguredDuration(sectionId, selectedCount) {
  if (isCodingSection(sectionId)) return 0;
  return getConfiguredQuestionCount(sectionId, selectedCount) * getSecondsPerQuestion(sectionId);
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

function buildAttemptCounts(totalQuestions, answeredCount, visitedQuestions = []) {
  const visitedFromState = Array.isArray(visitedQuestions) ? visitedQuestions.filter(Boolean).length : 0;
  const visitedCount = Math.max(answeredCount, Math.min(totalQuestions, visitedFromState || answeredCount));
  const notVisitedCount = Math.max(totalQuestions - visitedCount, 0);
  const notAnsweredCount = Math.max(visitedCount - answeredCount, 0);
  return {
    visitedCount,
    notVisitedCount,
    notAnsweredCount,
  };
}

function createSummary(sectionId, questions, answers, reason = "manual", visitedQuestions = []) {
  const answeredCount = answers.filter((answer) => (answer || "").trim().length > 0).length;
  const score = questions.filter((question, index) => answers[index] === question.answer).length;
  const counts = buildAttemptCounts(questions.length, answeredCount, visitedQuestions);
  return {
    sectionId,
    mode: "mcq",
    completedAt: new Date().toISOString(),
    totalQuestions: questions.length,
    answeredCount,
    ...counts,
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

function createCodingSessionSummary(sectionId, challenges, answers, language, runResults, submitResults, reason = "manual", visitedQuestions = []) {
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
  const answeredCount = items.filter((item) => item.sourceCode.trim()).length;
  const counts = buildAttemptCounts(items.length, answeredCount, visitedQuestions);
  return {
    sectionId,
    mode: "coding",
    completedAt: new Date().toISOString(),
    totalQuestions: items.length,
    answeredCount,
    ...counts,
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

function buildLocalCodingSessionFromLevels(levels, count, excludedKeys = []) {
  const sourceLevels = Array.isArray(levels) && levels.length ? levels : ["easy"];
  const excluded = new Set(excludedKeys);
  const items = [];
  let index = 0;
  let attempts = 0;
  while (items.length < count && attempts < count * 20) {
    const sourceLevel = sourceLevels[index % sourceLevels.length];
    const challenge = buildLocalCodingFallback(sourceLevel, Math.floor(index / sourceLevels.length));
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

function buildGuaranteedCodingSessionFromLevels(levels, count, excludedKeys = []) {
  const sourceLevels = Array.isArray(levels) && levels.length ? levels : ["easy"];
  const uniqueItems = buildLocalCodingSessionFromLevels(sourceLevels, count, excludedKeys);
  if (uniqueItems.length >= count) {
    return uniqueItems;
  }

  const filledItems = [...uniqueItems];
  let index = 0;
  while (filledItems.length < count) {
    const sourceLevel = sourceLevels[index % sourceLevels.length];
    filledItems.push(buildLocalCodingFallback(sourceLevel, Math.floor(index / sourceLevels.length)));
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

async function fetchUniqueCodingChallengesForLevels(levels, desiredCount, excludedKeys = []) {
  const sourceLevels = Array.isArray(levels) && levels.length ? levels : ["easy"];
  const uniqueChallenges = [];
  const seenChallengeKeys = new Set((excludedKeys || []).filter(Boolean));
  let attempts = 0;
  const maxAttempts = Math.max(desiredCount * 4, 12);

  while (uniqueChallenges.length < desiredCount && attempts < maxAttempts) {
    const remaining = desiredCount - uniqueChallenges.length;
    const batchSize = Math.min(Math.max(remaining, 2), 4);
    attempts += batchSize;

    const responses = await Promise.all(
      Array.from({ length: batchSize }, (_, batchIndex) =>
        axios.post(`${API_BASE_URL}/coding/challenge`, {
          difficulty: sourceLevels[(uniqueChallenges.length + batchIndex) % sourceLevels.length],
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

async function fetchGeneratedMcqSection(sectionId, count) {
  const endpoint = sectionId === "aptitude"
    ? "aptitude"
    : sectionId === "advanced-quant"
      ? "advanced-quant"
      : sectionId === "reasoning"
        ? "reasoning"
        : sectionId === "verbal"
          ? "verbal"
          : "computer-fundamentals";
  const response = await axios.post(`${API_BASE_URL}/mcq/${endpoint}`, { count });
  const sessionQuestions = Array.isArray(response.data?.questions) ? response.data.questions : [];
  if (!sessionQuestions.length) {
    throw new Error(`No ${sectionId} questions were generated.`);
  }
  return sessionQuestions.map((question, index) => ({
    ...question,
    sessionId: question.sessionId || `${sectionId}-mock-${index + 1}`,
  }));
}

async function buildMockCodingSection(sectionId, count) {
  const meta = getAptitudeMockSectionMeta(sectionId);
  const sourceLevels = getCodingSourceLevels(meta.codingLevel || "basic");
  const { challenges } = await fetchUniqueCodingChallengesForLevels(sourceLevels, count, []);
  const sessionQuestions = challenges.length
    ? challenges
    : buildGuaranteedCodingSessionFromLevels(sourceLevels, count, []);
  return {
    ...meta,
    questions: sessionQuestions,
    totalDuration: count * ((getCodingLevelConfig(meta.codingLevel || "basic").timerMinutes || 10) * 60),
    timeLeft: count * ((getCodingLevelConfig(meta.codingLevel || "basic").timerMinutes || 10) * 60),
    answers: new Array(sessionQuestions.length).fill(""),
    visitedQuestions: sessionQuestions.map((_, index) => index === 0),
    currentIndex: 0,
    codingRunResults: new Array(sessionQuestions.length).fill(null),
    codingRunSources: new Array(sessionQuestions.length).fill(""),
    codingSubmitResults: new Array(sessionQuestions.length).fill(null),
    codingLanguage: "",
    count,
  };
}

async function buildMockMcqSection(sectionId, count) {
  const meta = getAptitudeMockSectionMeta(sectionId);
  const questions = await fetchGeneratedMcqSection(sectionId, count);
  return {
    ...meta,
    questions,
    totalDuration: count * getSecondsPerQuestion(sectionId),
    timeLeft: count * getSecondsPerQuestion(sectionId),
    secondsPerQuestion: getSecondsPerQuestion(sectionId),
    answers: new Array(questions.length).fill(""),
    visitedQuestions: questions.map((_, index) => index === 0),
    currentIndex: 0,
    count,
  };
}

function createMockSummary(sectionResults, reason = "manual") {
  const safeResults = Array.isArray(sectionResults) ? sectionResults : [];
  return {
    sectionId: "aptitude-mock",
    mode: "mock",
    completedAt: new Date().toISOString(),
    totalQuestions: safeResults.reduce((total, item) => total + (item.totalQuestions || 0), 0),
    answeredCount: safeResults.reduce((total, item) => total + (item.answeredCount || 0), 0),
    visitedCount: safeResults.reduce((total, item) => total + (item.visitedCount || 0), 0),
    notVisitedCount: safeResults.reduce((total, item) => total + (item.notVisitedCount || 0), 0),
    notAnsweredCount: safeResults.reduce((total, item) => total + (item.notAnsweredCount || 0), 0),
    score: safeResults.reduce((total, item) => total + (item.score || 0), 0),
    autoSubmitted: reason === "auto",
    sections: safeResults,
  };
}

function getAptitudeSummaryMaxScore(summary) {
  if (!summary) return 0;
  if (summary.mode === "mock") {
    return (summary.sections || []).reduce((total, section) => total + getAptitudeSummaryMaxScore(section), 0);
  }
  if (summary.mode === "coding") {
    return (summary.codingItems || []).reduce((total, item) => total + (Number(item.execution?.total) || 0), 0) || summary.totalQuestions || 0;
  }
  return summary.totalQuestions || 0;
}

function getAptitudeQuestionOutline(summary) {
  if (!summary) return [];
  if (summary.mode === "mock") {
    return (summary.sections || []).flatMap((section) => getAptitudeQuestionOutline(section));
  }
  if (summary.mode === "coding") {
    return (summary.codingItems || []).map((item, index) => ({
      id: `${summary.sectionId || "coding"}-${index + 1}`,
      question: item.challenge?.title || item.challenge?.description || `Coding question ${index + 1}`,
      question_type: "coding",
      score: item.execution?.total ? Math.round(((item.execution?.passed || 0) / item.execution.total) * 100) : 0,
    }));
  }
  return (summary.items || []).map((item, index) => ({
    id: item.sessionId || `${summary.sectionId || "aptitude"}-${index + 1}`,
    question: item.question || item.prompt || `Question ${index + 1}`,
    question_type: "mcq",
    score: item.isCorrect ? 100 : 0,
  }));
}

function getAptitudeEvaluations(summary) {
  if (!summary) return [];
  if (summary.mode === "mock") {
    return (summary.sections || []).flatMap((section) => getAptitudeEvaluations(section));
  }
  if (summary.mode === "coding") {
    return (summary.codingItems || []).map((item, index) => ({
      question_id: `${summary.sectionId || "coding"}-${index + 1}`,
      question: item.challenge?.title || item.challenge?.description || `Coding question ${index + 1}`,
      question_type: "coding",
      answer: item.sourceCode || "",
      feedback: item.review?.summary || "",
      strengths: item.review?.strengths || [],
      gaps: item.review?.issues || item.review?.next_steps || [],
      suggestions: item.review?.next_steps || [],
      score: item.execution?.total ? Math.round(((item.execution?.passed || 0) / item.execution.total) * 100) : 0,
      provider: "aptitude",
    }));
  }
  return (summary.items || []).map((item, index) => ({
    question_id: item.sessionId || `${summary.sectionId || "aptitude"}-${index + 1}`,
    question: item.question || item.prompt || `Question ${index + 1}`,
    question_type: "mcq",
    answer: item.selectedAnswer || "",
    feedback: item.isCorrect ? "Correct answer selected." : `Correct answer: ${item.correctAnswer || item.answer || "N/A"}`,
    score: item.isCorrect ? 100 : 0,
    provider: "aptitude",
  }));
}

function buildAptitudeReportPayload(summary, candidateName = "") {
  const section = getSectionConfig(summary?.sectionId);
  const mockTitle = summary?.mode === "mock" ? "Aptitude Mock" : "";
  const sectionTitle = mockTitle || section.title || "Aptitude";
  const maxScore = getAptitudeSummaryMaxScore(summary);
  const scorePercent = maxScore ? Math.round(((summary.score || 0) / maxScore) * 100) : 0;
  const questionOutline = getAptitudeQuestionOutline(summary);
  const evaluations = getAptitudeEvaluations(summary);
  const answered = summary?.answeredCount || 0;
  const total = summary?.totalQuestions || 0;

  return {
    category: "aptitude",
    interview_type: "aptitude",
    selected_mode: "aptitude",
    score: scorePercent,
    overall_score: scorePercent,
    summary: `${sectionTitle} completed with ${summary?.score || 0}/${maxScore || total} points and ${answered}/${total} questions answered.`,
    top_strengths: scorePercent >= 70 ? ["Strong accuracy in this aptitude round."] : [],
    improvement_areas: scorePercent < 70 ? ["Review missed questions and repeat a focused aptitude round."] : [],
    strongest_questions: evaluations.filter((item) => item.score >= 100).map((item) => item.question).slice(0, 3),
    needs_work_questions: evaluations.filter((item) => item.score < 100).map((item) => item.question).slice(0, 3),
    answers: evaluations.map((item) => item.answer),
    evaluations,
    questions_answered: answered,
    total_questions: total,
    question_outline: questionOutline,
    transcript: JSON.stringify(summary),
    completed_at: summary?.completedAt,
    context: {
      category: "aptitude",
      selected_mode: "aptitude",
      aptitude_type: summary?.sectionId || "aptitude",
      section_id: summary?.sectionId || "aptitude",
      section_title: sectionTitle,
      test_type: summary?.mode || "mcq",
      coding_level: summary?.mode === "coding" ? section.codingLevel || "" : "",
      candidate_name: candidateName,
      practice_type: summary?.mode === "mock" ? "mock test" : "aptitude test",
    },
  };
}

function AptitudeTest({ examOnly = false }) {
  const navigate = useNavigate();

  // warn before leaving page when user tries to navigate away
  React.useEffect(() => {
    const handleBeforeUnload = (e) => {
      e.preventDefault();
      e.returnValue = "All submissions and saved data will be lost";
      return "All submissions and saved data will be lost";
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, []);
  const [stage, setStage] = useState(examOnly ? "loading" : "landing");
  const [selectedSection, setSelectedSection] = useState("aptitude");
  const [questionCount, setQuestionCount] = useState(10);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [timeLeft, setTimeLeft] = useState(0);
  const [summary, setSummary] = useState(null);
  const [runtimeLanguages, setRuntimeLanguages] = useState([]);
  const [codingLevel, setCodingLevel] = useState("basic");
  const [codingLanguage, setCodingLanguage] = useState("");
  const [visitedQuestions, setVisitedQuestions] = useState([]);
  const [codingRunResults, setCodingRunResults] = useState([]);
  const [codingRunSources, setCodingRunSources] = useState([]);
  const [codingSubmitResults, setCodingSubmitResults] = useState([]);
  const [, setCodingLoading] = useState(false);
  const [codingRunLoading, setCodingRunLoading] = useState(false);
  const [codingSubmitLoading, setCodingSubmitLoading] = useState(false);
  const [codingError, setCodingError] = useState("");
  const [startError, setStartError] = useState("");
  const [codingTimerStarted, setCodingTimerStarted] = useState(false);
  const [startingTest, setStartingTest] = useState(false);
  const [mockSections, setMockSections] = useState([]);
  const [mockSectionIndex, setMockSectionIndex] = useState(0);
  const [mockSectionResults, setMockSectionResults] = useState([]);
  const [examIntroStep, setExamIntroStep] = useState("fullscreen");
  const [examConsentChecked, setExamConsentChecked] = useState(false);
  const [isExamFullscreen, setIsExamFullscreen] = useState(false);
  const [examStateLoaded, setExamStateLoaded] = useState(!examOnly);
  const [showEndExamConfirm, setShowEndExamConfirm] = useState(false);
  const [startupCountdown, setStartupCountdown] = useState(null);
  const [startupMessage, setStartupMessage] = useState(APTITUDE_STARTUP_MESSAGES[0]);
  const [startupMessageVisible, setStartupMessageVisible] = useState(true);
  const [showFullscreenWarning, setShowFullscreenWarning] = useState(false);
  const [showConsentWarning, setShowConsentWarning] = useState(false);
  const [showDetailedResults, setShowDetailedResults] = useState(false);
  const [showCalculator, setShowCalculator] = useState(false);
  const [calculatorExpression, setCalculatorExpression] = useState("");
  const setupSectionRef = useRef(null);
  const startupRunIdRef = useRef(0);
  const startupOverlayRef = useRef(null);
  const savedSummaryKeysRef = useRef(new Set());

  const selectedSectionConfig = useMemo(() => getSectionConfig(selectedSection), [selectedSection]);
  const mockMode = isMockSection(selectedSection);
  const activeMockSection = mockMode && stage === "test" ? mockSections[mockSectionIndex] : null;
  const activeMode = activeMockSection?.mode || selectedSectionConfig.mode;
  const activeSectionId = activeMockSection?.id || selectedSection;
  const activeSectionTitle = activeMockSection?.title || selectedSectionConfig.title;
  const codingMode = activeMode === "coding";
  const selectedCodingLevel = getCodingLevelConfig(codingLevel);
  const codingSourceLevels = getCodingSourceLevels(codingLevel);
  const configuredQuestionCount = mockMode
    ? (APTITUDE_MOCK_COUNT_OPTIONS.includes(questionCount) ? questionCount : APTITUDE_MOCK_COUNT_OPTIONS[0])
    : getConfiguredQuestionCount(selectedSection, questionCount);
  const secondsPerQuestion = codingMode
    ? 0
    : activeMockSection?.secondsPerQuestion || getSecondsPerQuestion(activeSectionId);
  const configuredDuration = mockMode
    ? getMockTotalDuration(configuredQuestionCount)
    : codingMode
    ? configuredQuestionCount * ((selectedCodingLevel?.timerMinutes || 10) * 60)
    : getConfiguredDuration(selectedSection, questionCount);
  const totalMinutes = Math.floor(configuredDuration / 60);
  const currentQuestion = questions[currentIndex];
  const answeredCount = answers.filter((answer) => (answer || "").trim().length > 0).length;
  const visitedQuestionCount = visitedQuestions.filter(Boolean).length;
  const minQuestionCount = codingMode ? 5 : 10;
  const sliderMaxQuestionCount = codingMode ? 20 : 50;
  const overallTimeLeft = stage === "exam-entry" ? configuredDuration : timeLeft;
  const showExamWorkspace = examOnly && (stage === "exam-entry" || stage === "test");
  const showExamSummary = examOnly && stage === "summary" && summary;
  const showExamHeaderControls = stage === "test";
  const showPrestartCancel = stage === "exam-entry";
  const isLandingStage = stage === "landing";
  const isSetupStage = stage === "setup";
  const selectedRuntime = useMemo(() => runtimeLanguages.find((item) => item.id === codingLanguage) || null, [runtimeLanguages, codingLanguage]);
  const currentCodingRunResult = codingRunResults[currentIndex] || null;
  const isCodingBusy = codingRunLoading || codingSubmitLoading;
  const hasSelectedCodingLanguage = Boolean(codingLanguage);
  const candidateName = useMemo(() => {
    try {
      const rawUser = window.localStorage.getItem("user");
      const parsedUser = rawUser ? JSON.parse(rawUser) : null;
      const firstName = String(parsedUser?.first_name || parsedUser?.firstName || "").trim();
      const lastName = String(parsedUser?.last_name || parsedUser?.lastName || "").trim();
      const combinedName = [firstName, lastName].filter(Boolean).join(" ").trim();
      const name = combinedName || parsedUser?.full_name || parsedUser?.fullName || parsedUser?.name || parsedUser?.username;
      if (name) return String(name);
    } catch {
      // Ignore parsing issues and fall back.
    }
    return "Candidate";
  }, []);

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
    if (!examOnly) {
      return;
    }
    try {
      const raw = window.sessionStorage.getItem(APTITUDE_EXAM_SESSION_KEY);
      const saved = raw ? JSON.parse(raw) : null;
      if (!saved || typeof saved !== "object") {
        navigate("/aptitude-test", { replace: true });
        return;
      }

      setStage(saved.stage || "exam-entry");
      setSelectedSection(saved.selectedSection || "aptitude");
      setQuestionCount(saved.questionCount || 10);
      setQuestions(saved.questions || []);
      setAnswers(saved.answers || []);
      setCurrentIndex(saved.currentIndex || 0);
      setVisitedQuestions(saved.visitedQuestions || []);
      setTimeLeft(saved.timeLeft || 0);
      setSummary(saved.summary || null);
      setCodingLevel(saved.codingLevel || "basic");
      setCodingLanguage(saved.codingLanguage || "");
      setCodingRunResults(saved.codingRunResults || []);
      setCodingRunSources(saved.codingRunSources || []);
      setCodingSubmitResults(saved.codingSubmitResults || []);
      setMockSections(saved.mockSections || []);
      setMockSectionIndex(saved.mockSectionIndex || 0);
      setMockSectionResults(saved.mockSectionResults || []);
      setExamIntroStep(saved.examIntroStep || "fullscreen");
      setExamConsentChecked(Boolean(saved.examConsentChecked));
      setExamStateLoaded(true);
    } catch {
      navigate("/aptitude-test", { replace: true });
    }
  }, [examOnly, navigate]);

  useEffect(() => {
    const onFullscreenChange = () => {
      const isFullscreen = Boolean(document.fullscreenElement);
      setIsExamFullscreen(isFullscreen);
      if (!examOnly) return;
      if (!isFullscreen && (stage === "test" || (stage === "exam-entry" && examIntroStep === "instructions"))) {
        setShowFullscreenWarning(true);
      } else if (isFullscreen) {
        setShowFullscreenWarning(false);
      }
    };
    document.addEventListener("fullscreenchange", onFullscreenChange);
    onFullscreenChange();
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, [examIntroStep, examOnly, stage]);

  useEffect(() => {
    if (!startingTest || startupCountdown != null) return undefined;
    let messageIndex = 0;
    const interval = window.setInterval(() => {
      messageIndex = (messageIndex + 1) % APTITUDE_STARTUP_MESSAGES.length;
      setStartupMessageVisible(false);
      window.setTimeout(() => {
        setStartupMessage(APTITUDE_STARTUP_MESSAGES[messageIndex]);
        setStartupMessageVisible(true);
      }, 180);
    }, 1800);
    return () => window.clearInterval(interval);
  }, [startingTest, startupCountdown]);

  useEffect(() => {
    if (!showConsentWarning) return undefined;
    const timeoutId = window.setTimeout(() => {
      setShowConsentWarning(false);
    }, 2600);
    return () => window.clearTimeout(timeoutId);
  }, [showConsentWarning]);

  useEffect(() => {
    if (stage === "summary" && summary) {
      setShowDetailedResults(false);
    }
  }, [stage, summary]);

  useEffect(() => {
    if (stage !== "summary" || !summary) return;

    const token = localStorage.getItem("token");
    if (!token) return;

    const summaryKey = [
      summary.completedAt,
      summary.sectionId,
      summary.mode,
      summary.score,
      summary.totalQuestions,
      summary.answeredCount,
    ].join("|");

    if (savedSummaryKeysRef.current.has(summaryKey)) return;
    savedSummaryKeysRef.current.add(summaryKey);

    const saveSummary = async () => {
      try {
        await axios.post(
          `${API_BASE_URL}/interview-result`,
          buildAptitudeReportPayload(summary, candidateName),
          { headers: { Authorization: `Bearer ${token}` } }
        );
      } catch (saveError) {
        console.warn("Failed to save aptitude result to dashboard history.", saveError);
      }
    };

    void saveSummary();
  }, [candidateName, stage, summary]);

  useEffect(() => {
    if (!startingTest) return;
    window.requestAnimationFrame(() => {
      const lowerViewportOffset = Math.max((window.innerHeight - 420) / 2 + 460, 0);
      window.scrollTo({ top: lowerViewportOffset, left: 0, behavior: "smooth" });
    });
  }, [startingTest]);

  useEffect(() => {
    if (codingMode) return;
    setQuestionCount((current) => Math.max(current, 10));
  }, [codingMode, selectedSection]);

  useEffect(() => {
    if (!mockMode) return;
    if (!APTITUDE_MOCK_COUNT_OPTIONS.includes(questionCount)) {
      setQuestionCount(APTITUDE_MOCK_COUNT_OPTIONS[0]);
    }
  }, [mockMode, questionCount]);

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
    if (!questions.length) {
      setVisitedQuestions([]);
      return;
    }
    setVisitedQuestions((currentVisited) => {
      const normalized = questions.map((_, index) => Boolean(currentVisited[index]));
      normalized[currentIndex] = true;
      if (mockMode) {
        patchActiveMockSection({ visitedQuestions: normalized });
      }
      return normalized;
    });
  }, [currentIndex, mockMode, questions]);

  useEffect(() => {
    if (stage !== "test" || !codingMode || !currentQuestion || codingTimerStarted) return;
    if (!mockMode) {
      setTimeLeft(activeMockSection?.totalDuration || configuredDuration);
    }
    setCodingTimerStarted(true);
  }, [activeMockSection, codingMode, codingTimerStarted, configuredDuration, currentQuestion, mockMode, stage]);

  useEffect(() => {
    if (stage !== "test") return undefined;
    if (codingMode && (!codingTimerStarted || !currentQuestion)) return undefined;
    if (timeLeft <= 0) {
      if (mockMode) {
        setSummary(buildMockSubmitSummary("auto"));
        setStage("summary");
        window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
      } else if (codingMode && (answers[currentIndex] || "").trim()) {
        void handleSubmitCode("auto");
      } else if (!codingMode) {
        setStage("summary");
        setSummary(createSummary(selectedSection, questions, answers, "auto", visitedQuestions));
        window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
      }
      return undefined;
    }
    const timer = window.setInterval(() => {
      setTimeLeft((currentTime) => {
        return currentTime - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answers, codingLanguage, codingMode, codingRunResults, codingSubmitResults, currentIndex, currentQuestion, mockMode, questions, selectedSection, stage, timeLeft, codingTimerStarted, activeMockSection]);

  function scrollToSetupSection() {
    window.requestAnimationFrame(() => {
      setupSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function patchActiveMockSection(patchOrUpdater) {
    setMockSections((currentSections) => currentSections.map((section, index) => {
      if (index !== mockSectionIndex) {
        return section;
      }
      const nextPatch = typeof patchOrUpdater === "function" ? patchOrUpdater(section) : patchOrUpdater;
      return {
        ...section,
        ...nextPatch,
      };
    }));
  }

  async function requestExamFullscreen() {
    if (document.fullscreenElement) {
      setIsExamFullscreen(true);
      return true;
    }
    try {
      await document.documentElement.requestFullscreen();
      setIsExamFullscreen(true);
      return true;
    } catch {
      setStartError("Fullscreen permission was denied. Please allow fullscreen to continue.");
      return false;
    }
  }

  function launchExamRoute(sessionPayload) {
    window.sessionStorage.setItem(APTITUDE_EXAM_SESSION_KEY, JSON.stringify(sessionPayload));
    navigate("/aptitude-exam");
  }

  async function runExamLaunchCountdown(seconds = 3) {
    const activeRunId = startupRunIdRef.current;
    setStartupCountdown(seconds);
    for (let remaining = seconds; remaining > 0; remaining -= 1) {
      if (activeRunId !== startupRunIdRef.current) {
        setStartupCountdown(null);
        return false;
      }
      setStartupCountdown(remaining);
      // Give the user a clear visual start cue before navigation.
      // eslint-disable-next-line no-await-in-loop
      await new Promise((resolve) => window.setTimeout(resolve, 1000));
    }
    if (activeRunId !== startupRunIdRef.current) {
      setStartupCountdown(null);
      return false;
    }
    setStartupCountdown(0);
    await new Promise((resolve) => window.setTimeout(resolve, 250));
    if (activeRunId !== startupRunIdRef.current) {
      setStartupCountdown(null);
      return false;
    }
    setStartupCountdown(null);
    return true;
  }

  function loadMockSection(index, sections = mockSections) {
    const nextSection = sections[index];
    if (!nextSection) {
      return;
    }
    setMockSectionIndex(index);
    setQuestions(nextSection.questions || []);
    setAnswers(nextSection.answers || new Array((nextSection.questions || []).length).fill(""));
    setCurrentIndex(nextSection.currentIndex || 0);
    setVisitedQuestions(nextSection.visitedQuestions || []);
    if (!mockMode) {
      setTimeLeft(nextSection.timeLeft ?? nextSection.totalDuration ?? 0);
    }
    setSummary(null);
    setCodingRunResults(nextSection.codingRunResults || new Array((nextSection.questions || []).length).fill(null));
    setCodingRunSources(nextSection.codingRunSources || new Array((nextSection.questions || []).length).fill(""));
    setCodingSubmitResults(nextSection.codingSubmitResults || new Array((nextSection.questions || []).length).fill(null));
    setCodingRunLoading(false);
    setCodingSubmitLoading(false);
    setCodingError("");
    setCodingTimerStarted(nextSection.mode !== "coding");
    if (nextSection.mode === "coding") {
      setCodingLevel(nextSection.codingLevel || "basic");
      setCodingLanguage(nextSection.codingLanguage || "");
    }
    if (nextSection.mode !== "coding") {
      setCodingLanguage("");
    }
    setStage("test");
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }

  function finishMockSection(sectionSummary, reason = "manual") {
    const resultWithMeta = {
      ...sectionSummary,
      title: activeMockSection?.title || getAptitudeMockSectionMeta(activeMockSection?.id || "").title,
      sectionOrder: mockSectionIndex,
    };
    const nextResults = [...mockSectionResults, resultWithMeta];
    setMockSectionResults(nextResults);

    if (mockSectionIndex >= mockSections.length - 1) {
      setSummary(createMockSummary(nextResults, reason));
      setStage("summary");
      window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
      return;
    }

    loadMockSection(mockSectionIndex + 1, mockSections);
  }

  function handleOpenSetup() {
    if (examOnly) {
      if (document.fullscreenElement) {
        void document.exitFullscreen().catch(() => {});
      }
      window.sessionStorage.removeItem(APTITUDE_EXAM_SESSION_KEY);
      navigate("/aptitude-test");
      return;
    }
    if (startingTest) return;
    setStage("setup");
    setQuestions([]);
    setAnswers([]);
    setVisitedQuestions([]);
    setCurrentIndex(0);
    setSummary(null);
    setTimeLeft(0);
    setCodingRunResults([]);
    setCodingRunSources([]);
    setCodingSubmitResults([]);
    setCodingRunLoading(false);
    setCodingSubmitLoading(false);
    setCodingError("");
    setStartError("");
    setCodingTimerStarted(false);
    setMockSections([]);
    setMockSectionIndex(0);
    setMockSectionResults([]);
    setExamIntroStep("fullscreen");
    setExamConsentChecked(false);
    setStartupCountdown(null);
    setStartupMessage(APTITUDE_STARTUP_MESSAGES[0]);
    setStartupMessageVisible(true);
    setShowFullscreenWarning(false);
    setShowConsentWarning(false);
    scrollToSetupSection();
  }

  function openExamEntry() {
    setExamIntroStep("fullscreen");
    setExamConsentChecked(false);
    setShowConsentWarning(false);
    setStage("exam-entry");
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  }

  function beginPreparedExam() {
    setStage("test");
    setShowFullscreenWarning(false);
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  }

  function cancelStartupLaunch() {
    startupRunIdRef.current += 1;
    setStartingTest(false);
    setStartupCountdown(null);
    setStartupMessage(APTITUDE_STARTUP_MESSAGES[0]);
    setStartupMessageVisible(true);
    setStartError("");
  }

  async function handleStartTest() {
    if (startingTest) return;
    const startupRunId = startupRunIdRef.current + 1;
    startupRunIdRef.current = startupRunId;
    setStartingTest(true);
    setStartError("");
    setStartupCountdown(null);
    setStartupMessage(APTITUDE_STARTUP_MESSAGES[0]);
    setStartupMessageVisible(true);

    if (mockMode) {
      try {
        const distribution = APTITUDE_MOCK_DISTRIBUTION[configuredQuestionCount] || APTITUDE_MOCK_DISTRIBUTION[30];
        const builtSections = await Promise.all(
          APTITUDE_MOCK_SECTION_ORDER.map(async (sectionId) => {
            const count = distribution[sectionId] || 0;
            if (sectionId.startsWith("coding-")) {
              return buildMockCodingSection(sectionId, count);
            }
            return buildMockMcqSection(sectionId, count);
          }),
        );
        if (startupRunId !== startupRunIdRef.current) return;
        const firstSection = builtSections[0];
        const sessionPayload = {
          stage: "exam-entry",
          selectedSection,
          questionCount: configuredQuestionCount,
          questions: firstSection?.questions || [],
          answers: firstSection?.answers || [],
          currentIndex: firstSection?.currentIndex || 0,
          visitedQuestions: firstSection?.visitedQuestions || [],
          timeLeft: configuredDuration,
          summary: null,
          codingLevel: firstSection?.codingLevel || "basic",
          codingLanguage: firstSection?.codingLanguage || "",
          codingRunResults: firstSection?.codingRunResults || [],
          codingRunSources: firstSection?.codingRunSources || [],
          codingSubmitResults: firstSection?.codingSubmitResults || [],
          mockSections: builtSections,
          mockSectionIndex: 0,
          mockSectionResults: [],
          examIntroStep: "fullscreen",
          examConsentChecked: false,
        };
        const countdownCompleted = await runExamLaunchCountdown(3);
        if (!countdownCompleted || startupRunId !== startupRunIdRef.current) return;
        launchExamRoute(sessionPayload);
      } catch (error) {
        if (startupRunId !== startupRunIdRef.current) return;
        setStartError(error?.response?.data?.detail || error?.message || "Failed to generate aptitude mock sections.");
      } finally {
        if (startupRunId === startupRunIdRef.current) {
          setStartingTest(false);
        }
      }
      return;
    }

    if (codingMode) {
      const seenHistory = loadSeenCodingQuestions();
      const seenForLevel = Array.isArray(seenHistory[codingLevel]) ? seenHistory[codingLevel] : [];
      const questionPool = loadCodingQuestionPool();
      const poolForLevel = Array.isArray(questionPool[codingLevel]) ? questionPool[codingLevel] : [];
      const pooledChallenges = dedupeCodingChallenges(poolForLevel, seenForLevel, configuredQuestionCount);
      const fallbackChallenges = buildGuaranteedCodingSessionFromLevels(
        codingSourceLevels,
        configuredQuestionCount - pooledChallenges.length,
        [...seenForLevel, ...pooledChallenges.map((challenge) => getCodingChallengeKey(challenge))],
      );
      const initialChallenges = [...pooledChallenges, ...fallbackChallenges];
      const remainingPool = poolForLevel.filter((challenge) => {
        const key = getCodingChallengeKey(challenge);
        return key && !initialChallenges.some((item) => getCodingChallengeKey(item) === key);
      });
      if (startupRunId !== startupRunIdRef.current) return;

      setQuestions(initialChallenges);
      setAnswers(new Array(initialChallenges.length).fill(""));
      setCodingRunResults(new Array(initialChallenges.length).fill(null));
      setCodingRunSources(new Array(initialChallenges.length).fill(""));
      setCodingSubmitResults(new Array(initialChallenges.length).fill(null));
      setCurrentIndex(0);
      setTimeLeft(0);
      setSummary(null);
      setCodingTimerStarted(false);
      const sessionPayload = {
        stage: "exam-entry",
        selectedSection,
        questionCount: configuredQuestionCount,
        questions: initialChallenges,
        answers: new Array(initialChallenges.length).fill(""),
        currentIndex: 0,
        visitedQuestions: initialChallenges.map((_, index) => index === 0),
        timeLeft: 0,
        summary: null,
        codingLevel,
        codingLanguage: "",
        codingRunResults: new Array(initialChallenges.length).fill(null),
        codingRunSources: new Array(initialChallenges.length).fill(""),
        codingSubmitResults: new Array(initialChallenges.length).fill(null),
        mockSections: [],
        mockSectionIndex: 0,
        mockSectionResults: [],
        examIntroStep: "fullscreen",
        examConsentChecked: false,
      };

      const countdownCompleted = await runExamLaunchCountdown(3);
      if (!countdownCompleted || startupRunId !== startupRunIdRef.current) return;
      launchExamRoute(sessionPayload);

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
          const { challenges: aiChallenges } = await fetchUniqueCodingChallengesForLevels(
            codingSourceLevels,
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

    if (selectedSection === "aptitude" || selectedSection === "advanced-quant" || selectedSection === "reasoning" || selectedSection === "verbal" || selectedSection === "computer-fundamentals") {
      try {
        const endpoint = selectedSection === "aptitude"
          ? "aptitude"
          : selectedSection === "advanced-quant"
            ? "advanced-quant"
          : selectedSection === "reasoning"
            ? "reasoning"
            : selectedSection === "verbal"
              ? "verbal"
            : "computer-fundamentals";
        const response = await axios.post(`${API_BASE_URL}/mcq/${endpoint}`, {
          count: configuredQuestionCount,
        });
        if (startupRunId !== startupRunIdRef.current) return;
        const sessionQuestions = Array.isArray(response.data?.questions) ? response.data.questions : [];
        if (!sessionQuestions.length) {
          throw new Error("No questions were generated.");
        }
        setQuestions(sessionQuestions);
        setAnswers(new Array(sessionQuestions.length).fill(""));
        setCurrentIndex(0);
        setTimeLeft(configuredDuration);
        setSummary(null);
        const sessionPayload = {
          stage: "exam-entry",
          selectedSection,
          questionCount: configuredQuestionCount,
          questions: sessionQuestions,
          answers: new Array(sessionQuestions.length).fill(""),
          currentIndex: 0,
          visitedQuestions: sessionQuestions.map((_, index) => index === 0),
          timeLeft: configuredDuration,
          summary: null,
          codingLevel,
          codingLanguage: "",
          codingRunResults: [],
          codingRunSources: [],
          codingSubmitResults: [],
          mockSections: [],
          mockSectionIndex: 0,
          mockSectionResults: [],
          examIntroStep: "fullscreen",
          examConsentChecked: false,
        };
        const countdownCompleted = await runExamLaunchCountdown(3);
        if (!countdownCompleted || startupRunId !== startupRunIdRef.current) return;
        launchExamRoute(sessionPayload);
      } catch (error) {
        if (startupRunId !== startupRunIdRef.current) return;
        setStartError(
          error?.response?.data?.detail
          || error?.message
          || `Failed to generate ${selectedSection === "aptitude" ? "aptitude" : selectedSection === "advanced-quant" ? "advanced quantitative" : selectedSection === "reasoning" ? "reasoning" : selectedSection === "verbal" ? "verbal" : "computer fundamentals"} questions.`,
        );
      } finally {
        if (startupRunId === startupRunIdRef.current) {
          setStartingTest(false);
        }
      }
      return;
    }

    const sessionQuestions = buildMcqQuestions(selectedSection, configuredQuestionCount);
    setQuestions(sessionQuestions);
    setAnswers(new Array(sessionQuestions.length).fill(""));
    setCurrentIndex(0);
    setTimeLeft(configuredDuration);
    setSummary(null);
    const sessionPayload = {
      stage: "exam-entry",
      selectedSection,
      questionCount: configuredQuestionCount,
      questions: sessionQuestions,
      answers: new Array(sessionQuestions.length).fill(""),
      currentIndex: 0,
      visitedQuestions: sessionQuestions.map((_, index) => index === 0),
      timeLeft: configuredDuration,
      summary: null,
      codingLevel,
      codingLanguage: "",
      codingRunResults: [],
      codingRunSources: [],
      codingSubmitResults: [],
      mockSections: [],
      mockSectionIndex: 0,
      mockSectionResults: [],
      examIntroStep: "fullscreen",
      examConsentChecked: false,
    };
    const countdownCompleted = await runExamLaunchCountdown(3);
    if (!countdownCompleted || startupRunId !== startupRunIdRef.current) return;
    launchExamRoute(sessionPayload);
    if (startupRunId === startupRunIdRef.current) {
      setStartingTest(false);
    }
  }

  function handleSelectAnswer(value) {
    setAnswers((currentAnswers) => {
      const nextAnswers = [...currentAnswers];
      nextAnswers[currentIndex] = value;
      if (mockMode) {
        patchActiveMockSection({ answers: nextAnswers, visitedQuestions });
      }
      return nextAnswers;
    });
  }

  function handlePreviousQuestion() {
    const nextIndex = Math.max(0, currentIndex - 1);
    setCurrentIndex(nextIndex);
    if (mockMode) {
      patchActiveMockSection({ currentIndex: nextIndex, visitedQuestions });
    }
  }

  function handleNextQuestion() {
    const nextIndex = Math.min(questions.length - 1, currentIndex + 1);
    setCurrentIndex(nextIndex);
    if (mockMode) {
      patchActiveMockSection({ currentIndex: nextIndex, visitedQuestions });
    }
  }

  function buildMockSubmitSummary(reason = "manual") {
    const latestSections = mockSections.map((section, index) => {
      if (index === mockSectionIndex) {
        return {
          ...section,
          answers,
          visitedQuestions,
          currentIndex,
          timeLeft,
          codingRunResults,
          codingRunSources,
          codingSubmitResults,
          codingLanguage,
        };
      }
      return section;
    });

    const sectionResults = latestSections.map((section) => (
      section.mode === "coding"
        ? {
          ...createCodingSessionSummary(
            section.id,
            section.questions || [],
            section.answers || [],
            section.codingLanguage || codingLanguage,
            section.codingRunResults || [],
            section.codingSubmitResults || [],
            reason,
            section.visitedQuestions || [],
          ),
          title: section.title,
        }
        : {
          ...createSummary(section.id, section.questions || [], section.answers || [], reason, section.visitedQuestions || []),
          title: section.title,
        }
    ));
    return createMockSummary(sectionResults, reason);
  }

  function finalizeEndExam() {
    if (stage !== "test") {
      setShowEndExamConfirm(false);
      setShowFullscreenWarning(false);
      handleOpenSetup();
      return;
    }
    let nextSummary;
    if (mockMode) {
      nextSummary = buildMockSubmitSummary("manual");
    } else if (codingMode) {
      nextSummary = createCodingSessionSummary(selectedSection, questions, answers, codingLanguage, codingRunResults, codingSubmitResults, "manual", visitedQuestions);
    } else {
      nextSummary = createSummary(selectedSection, questions, answers, "manual", visitedQuestions);
    }
    setSummary(nextSummary);
    setShowEndExamConfirm(false);
    setShowFullscreenWarning(false);
    setStage("summary");
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  }

  function handleEndExam() {
    setShowEndExamConfirm(true);
  }

  function handleBackHome() {
    if (document.fullscreenElement) {
      void document.exitFullscreen().catch(() => {});
    }
    if (examOnly) {
      window.sessionStorage.removeItem(APTITUDE_EXAM_SESSION_KEY);
    }
    navigate("/");
  }

  async function handleShowDetailedResults() {
    if (document.fullscreenElement) {
      try {
        await document.exitFullscreen();
      } catch {
        // Ignore exit failures and still reveal the detailed results.
      }
    }
    setShowDetailedResults(true);
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  }

  async function handleRestoreFullscreen() {
    const success = await requestExamFullscreen();
    if (success) {
      setShowFullscreenWarning(false);
    }
  }

  function handleMockSectionJump(targetIndex) {
    if (!mockMode || targetIndex === mockSectionIndex || targetIndex < 0 || targetIndex >= mockSections.length) {
      return;
    }
    const syncedSections = mockSections.map((section, index) => (
      index === mockSectionIndex
        ? {
          ...section,
          answers,
          currentIndex,
          timeLeft,
          codingRunResults,
          codingRunSources,
          codingSubmitResults,
          codingLanguage,
        }
        : section
    ));
    setMockSections(syncedSections);
    loadMockSection(targetIndex, syncedSections);
  }

  async function handleProceedToInstructions() {
    const success = await requestExamFullscreen();
    if (success) {
      setExamIntroStep("instructions");
    }
  }

  function handleBeginExamClick() {
    if (!examConsentChecked) {
      setShowConsentWarning(true);
      return;
    }
    setShowConsentWarning(false);
    beginPreparedExam();
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
        if (mockMode) {
          patchActiveMockSection({ codingRunResults: next });
        }
        return next;
      });
      setCodingRunSources((current) => {
        const next = [...current];
        next[currentIndex] = sourceCode;
        if (mockMode) {
          patchActiveMockSection({ codingRunSources: next });
        }
        return next;
      });
    } catch (error) {
      setCodingError(error?.response?.data?.detail || "Failed to run code.");
      setCodingRunResults((current) => {
        const next = [...current];
        next[currentIndex] = null;
        if (mockMode) {
          patchActiveMockSection({ codingRunResults: next });
        }
        return next;
      });
      setCodingRunSources((current) => {
        const next = [...current];
        next[currentIndex] = "";
        if (mockMode) {
          patchActiveMockSection({ codingRunSources: next });
        }
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
        if (mockMode) {
          patchActiveMockSection({ codingSubmitResults: next });
        }
        return next;
      });
      const nextSubmitResults = [
        ...codingSubmitResults.slice(0, currentIndex),
        response.data,
        ...codingSubmitResults.slice(currentIndex + 1),
      ];
      if (currentIndex === questions.length - 1) {
        const codingSummary = createCodingSessionSummary(
          mockMode ? (activeMockSection?.id || selectedSection) : selectedSection,
          questions,
          answers,
          codingLanguage,
          codingRunResults,
          nextSubmitResults,
          reason,
          visitedQuestions,
        );
        if (mockMode) {
          const refreshedSections = mockSections.map((section, index) => (
            index === mockSectionIndex
              ? {
                ...section,
                answers,
                visitedQuestions,
                currentIndex,
                codingRunResults,
                codingRunSources,
                codingSubmitResults: nextSubmitResults,
                codingLanguage,
              }
              : section
          ));
          setMockSections(refreshedSections);
        } else {
          setSummary(codingSummary);
          setStage("summary");
          window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
        }
      } else {
        setCurrentIndex((current) => {
          const nextIndex = current + 1;
          if (mockMode) {
            patchActiveMockSection({ currentIndex: nextIndex, visitedQuestions });
          }
          return nextIndex;
        });
      }
    } catch (error) {
      setCodingError(error?.response?.data?.detail || "Failed to submit solution.");
    } finally {
      setCodingSubmitLoading(false);
    }
  }

  function handleFinishMcq(reason = "manual") {
    const mcqSummary = createSummary(mockMode ? (activeMockSection?.id || selectedSection) : selectedSection, questions, answers, reason, visitedQuestions);
    if (mockMode) {
      finishMockSection(mcqSummary, reason);
      return;
    }
    setStage("summary");
    setSummary(mcqSummary);
    window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  }

  if (examOnly && !examStateLoaded) {
    return null;
  }

  if (showExamWorkspace || showExamSummary) {
    return (
      <div className={`aptitude-exam-page ${stage === "summary" && showDetailedResults ? "is-scrollable" : ""}`}>
        <header className="aptitude-exam-navbar">
          <div className="aptitude-exam-brand" aria-label="INTERVIEWR brand">
            <img src={logo} alt="INTERVIEWR Logo" className="navbar-logo" />
            <div className="navbar-brand-title">
              <h2>
                INTERVIEW
                <span className="brand-r">R</span>
              </h2>
              <span className="navbar-brand-pipe">|</span>
              <span className="navbar-brand-sub">
                <span>AI Powered</span>
                <span>Interview System</span>
              </span>
            </div>
          </div>

          {showExamHeaderControls ? (
            <div className="aptitude-exam-nav-actions">
              <div className="aptitude-exam-timer-pill">
                <span>Overall Timer</span>
                <strong>{formatTime(overallTimeLeft)}</strong>
              </div>
              <button type="button" className="aptitude-end-btn" onClick={handleEndExam}>
                <PhoneOff size={18} strokeWidth={2.1} />
                End Interview
              </button>
            </div>
          ) : showPrestartCancel ? (
            <div className="aptitude-exam-nav-actions">
              <button type="button" className="aptitude-end-btn aptitude-cancel-btn" onClick={handleEndExam}>
                <PhoneOff size={18} strokeWidth={2.1} />
                Cancel Interview
              </button>
            </div>
          ) : null}
        </header>

        {showEndExamConfirm ? (
          <div className="aptitude-end-modal-backdrop" onClick={() => setShowEndExamConfirm(false)}>
            <div className="aptitude-end-modal" onClick={(event) => event.stopPropagation()}>
              <span className="aptitude-chip">{stage === "test" ? "Confirm End" : "Cancel Interview"}</span>
              <h3>{stage === "test" ? "Do you want to end the interview now?" : "Go back to the aptitude setup page?"}</h3>
              <p>
                {stage === "test"
                  ? "Your current progress will be submitted immediately and the results page will open."
                  : "The exam has not started yet. You will return to the aptitude setup page."}
              </p>
              <div className="aptitude-end-modal-actions">
                <button type="button" className="small-start-btn aptitude-secondary-btn" onClick={() => setShowEndExamConfirm(false)}>
                  {stage === "test" ? "Continue Test" : "Stay Here"}
                </button>
                <button type="button" className="aptitude-end-btn aptitude-cancel-btn" onClick={finalizeEndExam}>
                  <PhoneOff size={18} strokeWidth={2.1} />
                  {stage === "test" ? "End Now" : "Cancel Interview"}
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {showFullscreenWarning ? (
          <div className="aptitude-end-modal-backdrop">
            <div className="aptitude-end-modal aptitude-fullscreen-modal" onClick={(event) => event.stopPropagation()}>
              <span className="aptitude-chip">Fullscreen Required</span>
              <h3>Return to fullscreen to continue</h3>
              <p>This exam flow requires fullscreen mode during the instruction step and the live interview. Please re-enter fullscreen to continue.</p>
              <div className="aptitude-end-modal-actions">
                <button type="button" className="mock-btn aptitude-primary-btn" onClick={handleRestoreFullscreen}>
                  Re-enter Fullscreen
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {showConsentWarning ? (
          <div className="aptitude-floating-warning" role="alert" aria-live="assertive">
            Please agree to the exam instructions before starting the test.
          </div>
        ) : null}

        {stage === "exam-entry" ? (
          <main className="aptitude-exam-intro">
            <section className={`aptitude-exam-intro-card ${examIntroStep === "instructions" ? "is-instructions" : ""}`}>
              {examIntroStep === "fullscreen" ? (
                <>
                  <span className="aptitude-chip">Step 1</span>
                  <h1>Enter fullscreen before your aptitude test begins</h1>
                  <p>This exam experience is designed for fullscreen mode so the timer, sections, and question navigation stay stable throughout the test.</p>
                  <div className="aptitude-entry-callout">
                    <MonitorUp size={22} strokeWidth={2.1} />
                    <div>
                      <strong>Fullscreen is required to continue.</strong>
                      <p>Click the button below to enter fullscreen, then proceed to the exam instructions.</p>
                    </div>
                  </div>
                  <div className="aptitude-entry-actions">
                    <button type="button" className="mock-btn aptitude-secondary-btn" onClick={handleOpenSetup}>
                      Back to Aptitude
                    </button>
                    <button type="button" className="mock-btn aptitude-primary-btn" onClick={handleProceedToInstructions}>
                      Enter Fullscreen
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <span className="aptitude-chip">Step 2</span>
                  <h1>Read the exam instructions carefully</h1>
                  <p>Follow these rules for a smooth and fair aptitude exam experience.</p>

                  <div className="aptitude-entry-grid">
                    <article className="aptitude-entry-panel">
                      <h3>General Rules</h3>
                      <ul>
                        <li>Do not exit fullscreen during the test.</li>
                        <li>Do not switch tabs, windows, or applications during the test.</li>
                        <li>Do not refresh or close the exam page once the test begins.</li>
                        <li>Use the question palette to track answered and unanswered questions.</li>
                      </ul>
                    </article>

                    <article className="aptitude-entry-panel">
                      <h3>Mock Flow</h3>
                      <ul>
                        <li>The aptitude mock runs section by section in this order: Computer Fundamentals, Aptitude, Reasoning, Verbal, Advanced Quantitative Ability, Coding Basic, Coding Advanced.</li>
                        <li>The overall timer is shown in the navbar throughout the mock.</li>
                        <li>Mock sizes are fixed at 30, 60, 90, or 120 questions.</li>
                        <li>The coding part includes one Basic coding question and one Advanced coding question.</li>
                      </ul>
                    </article>
                  </div>

                  <div className="aptitude-entry-callout aptitude-entry-callout-warning">
                    <ShieldAlert size={22} strokeWidth={2.1} />
                    <div>
                      <strong>Consent and responsibility</strong>
                      <p>If any malpractice is done during the exam, the user is responsible for that conduct.</p>
                    </div>
                  </div>

                  <label className="aptitude-consent-row">
                    <input
                      type="checkbox"
                      checked={examConsentChecked}
                      onChange={(event) => {
                        const checked = event.target.checked;
                        setExamConsentChecked(checked);
                        if (checked) {
                          setShowConsentWarning(false);
                        }
                      }}
                    />
                    <span>I agree to follow the exam instructions and understand that I am responsible for any malpractice during this test.</span>
                  </label>

                  <div className="aptitude-entry-actions">
                    <button type="button" className="mock-btn aptitude-secondary-btn" onClick={() => setExamIntroStep("fullscreen")}>
                      Back
                    </button>
                    <button type="button" className="mock-btn aptitude-primary-btn" disabled={!isExamFullscreen} onClick={handleBeginExamClick}>
                      Start Test
                    </button>
                  </div>
                </>
              )}

              {startError ? <div className="aptitude-code-error">{startError}</div> : null}
            </section>
          </main>
        ) : stage === "summary" && summary ? (
          <main className="aptitude-exam-intro aptitude-exam-summary">
            <section className="aptitude-exam-intro-card aptitude-summary-shell aptitude-exam-summary-card">
              <div className="aptitude-summary-hero">
                <div>
                  <span className="aptitude-chip">{showDetailedResults ? "Summary" : "Test Complete"}</span>
                  <h2>{showDetailedResults ? (summary.autoSubmitted ? "Time is over. Your test was auto-submitted." : "Your test summary is ready.") : "Thank you. Your test is over."}</h2>
                  <p>
                    {showDetailedResults
                      ? (summary.mode === "coding"
                        ? "Below is your coding submission, passed test cases, and AI analysis."
                        : summary.mode === "mock"
                        ? "Below is your full aptitude mock review, grouped section by section in the same order as the live test."
                        : "Below is the answer review with your chosen option and the correct answer for every question.")
                      : "Your submission has been recorded successfully. Review the counters below, then open the detailed results whenever you are ready."}
                  </p>
                </div>
                <div className="aptitude-summary-score">
                  <span>{summary.mode === "coding" ? "Passed" : "Score"}</span>
                  <strong>{summary.score}/{summary.totalQuestions}</strong>
                  <small>{summary.answeredCount} answered</small>
                </div>
              </div>

              {!showDetailedResults ? (
                <>
                  <div className="aptitude-summary-counter-grid">
                    <div className="aptitude-summary-counter-card">
                      <span>Not Visited</span>
                      <strong>{summary.notVisitedCount || 0}</strong>
                    </div>
                    <div className="aptitude-summary-counter-card is-success">
                      <span>Answered</span>
                      <strong>{summary.answeredCount || 0}</strong>
                    </div>
                    <div className="aptitude-summary-counter-card is-warning">
                      <span>Not Answered</span>
                      <strong>{summary.notAnsweredCount || 0}</strong>
                    </div>
                  </div>

                  <div className="aptitude-summary-intro-actions">
                    <button type="button" className="mock-btn aptitude-primary-btn" onClick={handleShowDetailedResults}>
                      Show Results
                    </button>
                  </div>
                </>
              ) : summary.mode === "mock" ? (
                <div className="aptitude-review-list">
                  {(summary.sections || []).map((section, sectionIndex) => (
                    <article key={`mock-section-${section.sectionId}-${sectionIndex}`} className="aptitude-review-card">
                      <div className="aptitude-review-top">
                        <span>Section {sectionIndex + 1}</span>
                        <strong>{section.title}</strong>
                      </div>
                      <div className="aptitude-review-answer-grid">
                        <div>
                          <span>Score / passed</span>
                          <p>{section.score}/{section.totalQuestions}</p>
                        </div>
                        <div>
                          <span>Answered</span>
                          <p>{section.answeredCount}</p>
                        </div>
                      </div>
                      {section.mode === "coding" ? (
                        <div className="aptitude-review-list">
                          {(section.codingItems || []).map((item, index) => (
                            <article key={`mock-coding-${sectionIndex}-${index}`} className="aptitude-review-card is-coding">
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
                            </article>
                          ))}
                        </div>
                      ) : (
                        <div className="aptitude-review-list">
                          {(section.items || []).map((item, index) => (
                            <article key={`mock-mcq-${sectionIndex}-${item.sessionId || index}`} className={`aptitude-review-card ${item.isCorrect ? "is-correct" : "is-incorrect"}`}>
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
                      )}
                    </article>
                  ))}
                </div>
              ) : summary.mode === "coding" ? (
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

              {showDetailedResults ? (
                <div className="aptitude-flow-actions">
                  <button type="button" className="small-start-btn aptitude-secondary-btn aptitude-summary-btn" onClick={handleOpenSetup}>Practice Again</button>
                  <button type="button" className="small-start-btn aptitude-secondary-btn aptitude-summary-btn" onClick={handleBackHome}>
                    Back to Home
                  </button>
                  <button type="button" className="mock-btn aptitude-primary-btn aptitude-summary-btn" onClick={handleOpenSetup}>
                    Back to Aptitude
                  </button>
                </div>
              ) : null}
            </section>
          </main>
        ) : (
          <main className="aptitude-exam-shell">
            {mockMode ? (
              <div className="aptitude-exam-sections-bar">
                <div className="aptitude-exam-sections-track">
                  {mockSections.map((section, index) => (
                    <button
                      key={section.id}
                      type="button"
                      className={`aptitude-section-tab ${index === mockSectionIndex ? "is-active" : ""}`}
                      onClick={() => handleMockSectionJump(index)}
                    >
                      <span>{section.title}</span>
                    </button>
                  ))}
                </div>
                <div className="aptitude-calculator-anchor">
                  <button
                    type="button"
                    className={`aptitude-calculator-toggle ${showCalculator ? "is-active" : ""}`}
                    onClick={() => setShowCalculator((current) => !current)}
                  >
                    <Calculator size={18} strokeWidth={2} />
                    Calculator
                  </button>

                  {showCalculator ? (
                    <div className="aptitude-calculator-popover">
                      <div className="aptitude-exam-panel-head">
                        <span className="aptitude-chip">Calculator</span>
                        <button type="button" className="aptitude-calculator-close" onClick={() => setShowCalculator(false)}>Close</button>
                      </div>
                      <div className="aptitude-calculator-display">
                        {calculatorExpression || "0"}
                      </div>
                      <div className="aptitude-calculator-grid">
                        {["(", ")", "^", "/", "sin(", "cos(", "tan(", "*", "sqrt(", "log(", "ln(", "-", "7", "8", "9", "+", "4", "5", "6", "%", "1", "2", "3", ".", "0", "pi", "e", "="].map((value) => (
                          <button
                            key={value}
                            type="button"
                            className={`aptitude-calculator-key ${value === "=" ? "is-equals" : ""}`}
                            onClick={() => {
                              if (value === "=") {
                                try {
                                  const expression = (calculatorExpression || "0")
                                    .replace(/\^/g, "**")
                                    .replace(/pi/g, "Math.PI")
                                    .replace(/\be\b/g, "Math.E")
                                    .replace(/sqrt\(/g, "Math.sqrt(")
                                    .replace(/sin\(/g, "Math.sin(")
                                    .replace(/cos\(/g, "Math.cos(")
                                    .replace(/tan\(/g, "Math.tan(")
                                    .replace(/log\(/g, "Math.log10(")
                                    .replace(/ln\(/g, "Math.log(");
                                  // eslint-disable-next-line no-new-func
                                  const result = Function(`"use strict"; return (${expression})`)();
                                  setCalculatorExpression(String(result));
                                } catch {
                                  setCalculatorExpression("Error");
                                }
                                return;
                              }
                              setCalculatorExpression((current) => (current === "Error" ? value : `${current}${value}`));
                            }}
                          >
                            {value}
                          </button>
                        ))}
                        <button
                          type="button"
                          className="aptitude-calculator-key aptitude-calculator-key-wide"
                          onClick={() => setCalculatorExpression("")}
                        >
                          Clear
                        </button>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}

            <section className="aptitude-exam-main">
              <div className="aptitude-exam-mainbar">
                <div>
                  <span className="aptitude-chip">{mockMode ? "Active Section" : "Live Section"}</span>
                  <h2>{activeSectionTitle}</h2>
                  <p>{codingMode ? "Solve the challenge, run your code, and submit when ready." : "Read the question carefully and move freely across the question map."}</p>
                </div>
              </div>

              <div className="aptitude-progress-row">
                <div className="aptitude-progress-text">
                  {mockMode
                    ? `${activeSectionTitle} - Question ${currentIndex + 1} of ${questions.length}`
                    : `Question ${currentIndex + 1} of ${questions.length}`}
                </div>
                <div className="aptitude-progress-bar">
                  <span style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }} />
                </div>
              </div>

              <div className="aptitude-test-shell aptitude-exam-card">
                <div className="aptitude-question-card">
                  <div className="aptitude-question-meta">
                    {codingMode ? (
                      <>
                        <span>{selectedCodingLevel.timerMinutes || 10} minute coding level timer</span>
                        <span>Question {currentIndex + 1} of {questions.length}: run code, then submit to move to the next coding question</span>
                      </>
                    ) : (
                      <span>Question {currentIndex + 1} of {questions.length}</span>
                    )}
                  </div>
                  <div className="aptitude-question-scroll-area">
                    <h3>{currentQuestion?.question}</h3>

                    {codingMode ? (
                      <div className="aptitude-code-workspace">
                      <div className="aptitude-code-panel">
                        <div className="aptitude-code-panel-header">
                          <span className="aptitude-chip">Problem</span>
                          <strong>{currentQuestion?.difficulty || codingLevel}</strong>
                        </div>
                        <p className="aptitude-code-prompt">{currentQuestion?.description || currentQuestion?.prompt}</p>

                        {!!currentQuestion?.constraints?.length && (
                          <div className="aptitude-code-block">
                            <h4>Constraints</h4>
                            <ul>
                              {currentQuestion.constraints.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {!!currentQuestion?.hints?.length && (
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
                            {(currentQuestion?.examples || []).map((example, index) => (
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
                            {(currentQuestion?.public_test_cases || []).map((testCase, index) => (
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
                              if (mockMode) {
                                patchActiveMockSection({ codingLanguage: nextLanguage });
                              }
                              setAnswers((currentAnswers) => {
                                const nextAnswers = [...currentAnswers];
                                nextAnswers[currentIndex] = nextLanguage ? getStarterCode(currentQuestion, nextLanguage) : "";
                                if (mockMode) {
                                  patchActiveMockSection({ answers: nextAnswers });
                                }
                                return nextAnswers;
                              });
                              setCodingRunResults((current) => {
                                const next = [...current];
                                next[currentIndex] = null;
                                if (mockMode) {
                                  patchActiveMockSection({ codingRunResults: next });
                                }
                                return next;
                              });
                              setCodingSubmitResults((current) => {
                                const next = [...current];
                                next[currentIndex] = null;
                                if (mockMode) {
                                  patchActiveMockSection({ codingSubmitResults: next });
                                }
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
                            <div className="aptitude-code-editor aptitude-code-editor-empty">
                              <div>
                                <div className="aptitude-code-editor-title">Start your coding journey</div>
                                <div className="aptitude-code-editor-copy">Choose a language to load the starter template, then begin solving the challenge with confidence.</div>
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
                                if (mockMode) {
                                  patchActiveMockSection({ answers: nextAnswers });
                                }
                                return nextAnswers;
                              });
                              setCodingRunResults((current) => {
                                const next = [...current];
                                next[currentIndex] = null;
                                if (mockMode) {
                                  patchActiveMockSection({ codingRunResults: next });
                                }
                                return next;
                              });
                              setCodingSubmitResults((current) => {
                                const next = [...current];
                                next[currentIndex] = null;
                                if (mockMode) {
                                  patchActiveMockSection({ codingSubmitResults: next });
                                }
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
                        {currentQuestion?.options.map((option) => (
                          <button key={option} type="button" className={`aptitude-option ${answers[currentIndex] === option ? "is-selected" : ""}`} onClick={() => handleSelectAnswer(option)}>
                            {option}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

            </section>

            <aside className="aptitude-exam-sidebar aptitude-exam-sidebar--right">
              <div className="aptitude-exam-panel aptitude-exam-panel--sidebar">
                <div className="aptitude-profile-badge">
                  <div className="aptitude-profile-icon-shell">
                    <UserCircle2 size={52} strokeWidth={1.7} />
                  </div>
                  <div>
                    <div className="aptitude-profile-name">{candidateName}</div>
                  </div>
                </div>

                <div className="aptitude-question-legend">
                  <div className="aptitude-question-legend-item">
                    <span className="aptitude-legend-dot is-answered" />
                    <small>Visited & answered</small>
                  </div>
                  <div className="aptitude-question-legend-item">
                    <span className="aptitude-legend-dot is-pending" />
                    <small>Visited, not answered</small>
                  </div>
                  <div className="aptitude-question-legend-item">
                    <span className="aptitude-legend-dot is-unvisited" />
                    <small>Not visited</small>
                  </div>
                </div>

                <div className="aptitude-exam-panel-head">
                  <span className="aptitude-chip">Questions</span>
                  <strong>{activeSectionTitle}</strong>
                </div>
                <div className="aptitude-question-grid">
                  {questions.map((question, index) => {
                    const isAnswered = Boolean((answers[index] || "").trim());
                    const isVisited = Boolean(visitedQuestions[index]);
                    return (
                      <button
                        key={question.sessionId || `${activeSectionId}-${index}`}
                        type="button"
                        className={`aptitude-question-node ${index === currentIndex ? "is-current" : ""} ${isAnswered ? "is-answered" : ""} ${isVisited && !isAnswered ? "is-pending" : ""}`}
                        onClick={() => {
                          setCurrentIndex(index);
                          if (mockMode) {
                            patchActiveMockSection({ currentIndex: index, visitedQuestions });
                          }
                        }}
                      >
                        {index + 1}
                      </button>
                    );
                  })}
                </div>

                <div className="aptitude-sidebar-actions">
                  {codingMode ? (
                    <>
                      <button type="button" className="mock-btn aptitude-secondary-btn aptitude-sidebar-btn" onClick={handlePreviousQuestion} disabled={currentIndex === 0}>
                        Previous
                      </button>
                      <button type="button" className="mock-btn aptitude-secondary-btn aptitude-sidebar-btn" onClick={handleNextQuestion} disabled={currentIndex === questions.length - 1}>
                        Next
                      </button>
                      <button type="button" className="mock-btn aptitude-primary-btn aptitude-sidebar-btn" onClick={handleEndExam}>
                        Submit
                      </button>
                    </>
                  ) : (
                    <>
                    <button type="button" className="mock-btn aptitude-secondary-btn aptitude-sidebar-btn" onClick={handlePreviousQuestion} disabled={currentIndex === 0}>
                      Previous
                    </button>
                    <button type="button" className="mock-btn aptitude-secondary-btn aptitude-sidebar-btn" onClick={handleNextQuestion} disabled={currentIndex === questions.length - 1}>
                      Next
                    </button>
                    <button type="button" className="mock-btn aptitude-primary-btn aptitude-sidebar-btn" onClick={handleEndExam}>
                      Submit
                    </button>
                    </>
                  )}
                </div>
              </div>
            </aside>
          </main>
        )}
      </div>
    );
  }

  return (
    <div className="mock-page reveal">
      {startingTest ? (
        <div className="aptitude-startup-overlay" ref={startupOverlayRef} role="status" aria-live="polite" aria-busy="true">
          <div className="aptitude-startup-backdrop-orb aptitude-startup-backdrop-orb-one" />
          <div className="aptitude-startup-backdrop-orb aptitude-startup-backdrop-orb-two" />
          <div className="aptitude-startup-modal">
            <div className="aptitude-startup-illustration" aria-hidden="true">
              <div className="aptitude-startup-ring aptitude-startup-ring-one" />
              <div className="aptitude-startup-ring aptitude-startup-ring-two" />
              <div className="aptitude-startup-logo-shell">
                <img src={logo} alt="" className="aptitude-startup-logo" />
              </div>
            </div>
            <div className="aptitude-startup-copy">
              <div className={`aptitude-startup-line ${startupMessageVisible ? "is-visible" : ""}`}>
                {startupCountdown == null ? startupMessage : "Launching your exam workspace..."}
              </div>
              <div className="aptitude-startup-timer-pill">
                <span>{startupCountdown == null ? "Interview starts after preparation" : "Interview starts in"}</span>
                <strong>{startupCountdown == null ? "Preparing..." : `00:0${Math.max(0, startupCountdown)}`}</strong>
              </div>
              <button type="button" className="mock-btn aptitude-secondary-btn aptitude-startup-cancel-btn" onClick={cancelStartupLaunch}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}
      <MiniNavbar />

      <div className="mock-hero aptitude-hero" style={{ background: "linear-gradient(90deg, #0f766e 0%, #14b8a6 55%, #67e8f9 100%)" }}>
        <div>
          <h1>Aptitude Test</h1>
          <p>Choose a section, decide how many questions you want to practice, and take a timed round with instant summary review.</p>
          <button className="mock-btn" onClick={handleOpenSetup} disabled={startingTest}>Start Aptitude Test</button>
        </div>
        <img src={aptitudeHero} alt="Aptitude Test" className="mock-hero-img" />
      </div>

      {isLandingStage && (
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
                <li>MCQ sections use 4-option questions, and Computer Fundamentals uses 30 seconds per question</li>
                <li>The coding section uses a split problem/editor layout like coding platforms</li>
                <li>The editor starts with a starter template, not a solved answer</li>
              </ul>
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "center", marginTop: "22px" }}>
            <button className="small-start-btn" onClick={handleOpenSetup} disabled={startingTest}>Start Aptitude</button>
          </div>
        </div>
      )}

      {isSetupStage && (
        <>
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
                  <small>{mockMode ? `${configuredQuestionCount} total mock questions` : codingMode ? `${configuredQuestionCount} coding questions` : `${configuredQuestionCount} questions x ${secondsPerQuestion} sec`}</small>
                </div>
              </div>

              <div className="aptitude-setup-grid">
                {getOrderedSetupSections().map((section) => (
                  <button
                  key={section.id}
                  type="button"
                  className={`aptitude-section-card aptitude-section-card--${section.id} ${selectedSection === section.id ? "is-active" : ""}`}
                  disabled={startingTest}
                  onClick={() => setSelectedSection(section.id)}
                >
                    {selectedSection === section.id ? (
                      <div className="aptitude-section-selected-pill">Selected</div>
                    ) : null}
                    <strong>{section.title}</strong>
                    <span>{section.description}</span>
                  </button>
                ))}
              </div>

              {codingMode ? (
                <div className="aptitude-count-card">
                <div className="aptitude-count-copy">
                  <span className="aptitude-chip">Coding setup</span>
                  <h3>{selectedCodingLevel.title} level, {questionCount} questions</h3>
                  <div className="aptitude-tip-row">
                    <span
                      className="aptitude-tip-sign"
                      title="Choose Basic, Advanced, or Basic + Advanced, then set how many coding questions you want in this session from 5 to 20. Advanced mixes medium and hard questions, while Basic + Advanced includes both tracks."
                      aria-label="Tip: Choose Basic, Advanced, or Basic plus Advanced, then set how many coding questions you want in this session from 5 to 20. Advanced mixes medium and hard questions, while Basic plus Advanced includes both tracks."
                      tabIndex={0}
                    >
                      <Info size={16} strokeWidth={2.2} />
                    </span>
                    <p>Choose Basic, Advanced, or Basic + Advanced, then set how many coding questions you want in this session from 5 to 20. Advanced mixes medium and hard questions, while Basic + Advanced includes both tracks.</p>
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
              ) : mockMode ? (
                <div className="aptitude-count-card">
                  <div className="aptitude-count-copy">
                    <span className="aptitude-chip">Mock length</span>
                    <h3>{configuredQuestionCount} questions selected</h3>
                    <p>Choose a full mock size. Each mock includes fixed section-wise distribution and 2 coding questions.</p>
                  </div>
                  <div className="aptitude-count-controls">
                    <input
                      type="range"
                      min="0"
                      max={APTITUDE_MOCK_COUNT_OPTIONS.length - 1}
                      step="1"
                      value={Math.max(0, APTITUDE_MOCK_COUNT_OPTIONS.indexOf(configuredQuestionCount))}
                      disabled={startingTest}
                      onChange={(event) => {
                        const nextIndex = Number(event.target.value);
                        setQuestionCount(APTITUDE_MOCK_COUNT_OPTIONS[nextIndex] || APTITUDE_MOCK_COUNT_OPTIONS[0]);
                      }}
                    />
                    <div className="aptitude-count-stepper">
                      <button
                        type="button"
                        onClick={() => {
                          const currentIndex = Math.max(0, APTITUDE_MOCK_COUNT_OPTIONS.indexOf(configuredQuestionCount));
                          setQuestionCount(APTITUDE_MOCK_COUNT_OPTIONS[Math.max(0, currentIndex - 1)]);
                        }}
                        disabled={startingTest || configuredQuestionCount === APTITUDE_MOCK_COUNT_OPTIONS[0]}
                      >
                        -
                      </button>
                      <div>{configuredQuestionCount}</div>
                      <button
                        type="button"
                        onClick={() => {
                          const currentIndex = Math.max(0, APTITUDE_MOCK_COUNT_OPTIONS.indexOf(configuredQuestionCount));
                          setQuestionCount(APTITUDE_MOCK_COUNT_OPTIONS[Math.min(APTITUDE_MOCK_COUNT_OPTIONS.length - 1, currentIndex + 1)]);
                        }}
                        disabled={startingTest || configuredQuestionCount === APTITUDE_MOCK_COUNT_OPTIONS[APTITUDE_MOCK_COUNT_OPTIONS.length - 1]}
                      >
                        +
                      </button>
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
              {startError ? <div className="aptitude-code-error">{startError}</div> : null}
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
                <h2>{activeSectionTitle}</h2>
              </div>
              <div className="aptitude-timer-live">
                <span>Time left</span>
                <strong>{formatTime(timeLeft)}</strong>
                <small>{answeredCount}/{questions.length} answered{mockMode ? ` • Section ${mockSectionIndex + 1}/${mockSections.length}` : ""}</small>
              </div>
            </div>

            <div className="aptitude-progress-row">
              <div className="aptitude-progress-text">
                {mockMode
                  ? `${activeSectionTitle} - Question ${currentIndex + 1} of ${questions.length}`
                  : `Question ${currentIndex + 1} of ${questions.length}`}
              </div>
              <div className="aptitude-progress-bar">
                <span style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }} />
              </div>
            </div>

            <div className="aptitude-question-card">
              <div className="aptitude-question-meta">
                {codingMode ? (
                  <>
                    <span>{selectedCodingLevel.timerMinutes || 10} minute coding level timer</span>
                    <span>Question {currentIndex + 1} of {questions.length}: run code, then submit to move to the next coding question</span>
                  </>
                ) : (
                  <>
                    <span>{secondsPerQuestion} sec per question</span>
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
                          if (mockMode) {
                            patchActiveMockSection({ codingLanguage: nextLanguage });
                          }
                          setAnswers((currentAnswers) => {
                            const nextAnswers = [...currentAnswers];
                            nextAnswers[currentIndex] = nextLanguage ? getStarterCode(currentQuestion, nextLanguage) : "";
                            if (mockMode) {
                              patchActiveMockSection({ answers: nextAnswers });
                            }
                            return nextAnswers;
                          });
                          setCodingRunResults((current) => {
                            const next = [...current];
                            next[currentIndex] = null;
                            if (mockMode) {
                              patchActiveMockSection({ codingRunResults: next });
                            }
                            return next;
                          });
                          setCodingSubmitResults((current) => {
                            const next = [...current];
                            next[currentIndex] = null;
                            if (mockMode) {
                              patchActiveMockSection({ codingSubmitResults: next });
                            }
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
                            if (mockMode) {
                              patchActiveMockSection({ answers: nextAnswers });
                            }
                            return nextAnswers;
                          });
                          setCodingRunResults((current) => {
                            const next = [...current];
                            next[currentIndex] = null;
                            if (mockMode) {
                              patchActiveMockSection({ codingRunResults: next });
                            }
                            return next;
                          });
                          setCodingSubmitResults((current) => {
                            const next = [...current];
                            next[currentIndex] = null;
                            if (mockMode) {
                              patchActiveMockSection({ codingSubmitResults: next });
                            }
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
                    <button key={question.sessionId} type="button" className={`aptitude-map-dot ${index === currentIndex ? "is-current" : ""} ${answers[index] ? "is-answered" : ""}`} onClick={() => {
                      setCurrentIndex(index);
                      if (mockMode) {
                        patchActiveMockSection({ currentIndex: index });
                      }
                    }}>
                      {index + 1}
                    </button>
                  ))}
                </div>

                <div className="aptitude-flow-actions">
                  <button type="button" className="small-start-btn aptitude-secondary-btn" onClick={handlePreviousQuestion} disabled={currentIndex === 0}>Previous</button>
                  <div className="aptitude-inline-actions">
                    <button type="button" className="small-start-btn aptitude-secondary-btn" onClick={() => handleFinishMcq("manual")}>Submit Now</button>
                    <button type="button" className="mock-btn aptitude-primary-btn" onClick={handleNextQuestion} disabled={currentIndex === questions.length - 1}>Next Question</button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {!examOnly && stage === "summary" && summary && (
        <div className="mock-section">
          <div className="aptitude-flow-card aptitude-summary-shell">
            <div className="aptitude-summary-hero">
              <div>
                <span className="aptitude-chip">{showDetailedResults ? "Summary" : "Test Complete"}</span>
                <h2>{showDetailedResults ? (summary.autoSubmitted ? "Time is over. Your test was auto-submitted." : "Your test summary is ready.") : "Thank you. Your test is over."}</h2>
                <p>
                  {showDetailedResults
                    ? (summary.mode === "coding"
                      ? "Below is your coding submission, passed test cases, and AI analysis."
                      : summary.mode === "mock"
                      ? "Below is your full aptitude mock review, grouped section by section in the same order as the live test."
                      : "Below is the answer review with your chosen option and the correct answer for every question.")
                    : "Your submission has been recorded successfully. Review the counters below, then open the detailed results whenever you are ready."}
                </p>
              </div>
              <div className="aptitude-summary-score">
                <span>{summary.mode === "coding" ? "Passed" : "Score"}</span>
                <strong>{summary.score}/{summary.totalQuestions}</strong>
                <small>{summary.answeredCount} answered</small>
              </div>
            </div>

            {!showDetailedResults ? (
              <>
                <div className="aptitude-summary-counter-grid">
                  <div className="aptitude-summary-counter-card">
                    <span>Not Visited</span>
                    <strong>{summary.notVisitedCount || 0}</strong>
                  </div>
                  <div className="aptitude-summary-counter-card is-success">
                    <span>Answered</span>
                    <strong>{summary.answeredCount || 0}</strong>
                  </div>
                  <div className="aptitude-summary-counter-card is-warning">
                    <span>Not Answered</span>
                    <strong>{summary.notAnsweredCount || 0}</strong>
                  </div>
                </div>

                <div className="aptitude-summary-intro-actions">
                  <button type="button" className="mock-btn aptitude-primary-btn" onClick={() => setShowDetailedResults(true)}>
                    Show Results
                  </button>
                </div>
              </>
            ) : summary.mode === "mock" ? (
              <div className="aptitude-review-list">
                {(summary.sections || []).map((section, sectionIndex) => (
                  <article key={`mock-section-${section.sectionId}-${sectionIndex}`} className="aptitude-review-card">
                    <div className="aptitude-review-top">
                      <span>Section {sectionIndex + 1}</span>
                      <strong>{section.title}</strong>
                    </div>
                    <div className="aptitude-review-answer-grid">
                      <div>
                        <span>Score / passed</span>
                        <p>{section.score}/{section.totalQuestions}</p>
                      </div>
                      <div>
                        <span>Answered</span>
                        <p>{section.answeredCount}</p>
                      </div>
                    </div>
                    {section.mode === "coding" ? (
                      <div className="aptitude-review-list">
                        {(section.codingItems || []).map((item, index) => (
                          <article key={`mock-coding-${sectionIndex}-${index}`} className="aptitude-review-card is-coding">
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
                          </article>
                        ))}
                      </div>
                    ) : (
                      <div className="aptitude-review-list">
                        {(section.items || []).map((item, index) => (
                          <article key={`mock-mcq-${sectionIndex}-${item.sessionId || index}`} className={`aptitude-review-card ${item.isCorrect ? "is-correct" : "is-incorrect"}`}>
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
                    )}
                  </article>
                ))}
              </div>
            ) : summary.mode === "coding" ? (
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

            {showDetailedResults ? (
              <div className="aptitude-flow-actions">
                <button type="button" className="small-start-btn aptitude-secondary-btn aptitude-summary-btn" onClick={handleOpenSetup}>Practice Again</button>
                <button type="button" className="small-start-btn aptitude-secondary-btn aptitude-summary-btn" onClick={handleBackHome}>Back to Home</button>
                <button type="button" className="mock-btn aptitude-primary-btn aptitude-summary-btn" onClick={() => {
                  if (examOnly) {
                    handleOpenSetup();
                    return;
                  }
                  setStage("landing");
                }}>Back to Overview</button>
              </div>
            ) : null}
          </div>
        </div>
      )}

      <div className="bottom-footer">Prepared by AI Powered Interview System</div>
    </div>
  );
}

export default AptitudeTest;

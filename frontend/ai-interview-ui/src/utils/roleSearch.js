import { JOB_ROLES } from "../data/jobRoles";

const EXTRA_JOB_ROLE_ALIASES = [
  "SDE",
  "Software Development Engineer",
  "SDET",
  "AI/ML Engineer",
  "Generative AI Engineer",
  "Prompt Engineer",
  "LLM Engineer",
  "MERN Stack Developer",
  "MEAN Stack Developer",
  "Frontend Engineer",
  "Backend Engineer",
  "Full Stack Engineer",
  "Site Reliability Engineer",
  "Platform Engineer",
  "Cloud DevOps Engineer",
  "Product Analyst",
  "Cybersecurity Analyst",
  "SOC Analyst",
  "ERP Consultant",
  "SAP Consultant",
  "Salesforce Developer",
  "Power BI Developer",
  "Tableau Developer",
  "Software Engineer Intern",
  "Data Analyst Intern",
  "Business Analyst Intern",
];

export const TECHNICAL_JOB_ROLES = Array.from(
  new Set([
    "AI Engineer",
    "AI Research Scientist",
    "Android Developer",
    "Angular Developer",
    "Application Support Analyst",
    "Automation Engineer",
    "AWS Engineer",
    "Azure Engineer",
    "Backend Developer",
    "Big Data Engineer",
    "Business Intelligence Analyst",
    "C# Developer",
    "C++ Developer",
    "Cloud Architect",
    "Cloud DevOps Engineer",
    "Cloud Engineer",
    "Computer Vision Engineer",
    "Cybersecurity Analyst",
    "Data Analyst",
    "Data Analyst Intern",
    "Data Architect",
    "Data Engineer",
    "Data Engineer Intern",
    "Data Science Intern",
    "Data Scientist",
    "Database Administrator",
    "Deep Learning Engineer",
    "Design Systems Engineer",
    "DevOps Engineer",
    "Django Developer",
    "Docker Engineer",
    "Embedded Software Engineer",
    "ETL Developer",
    "Express.js Developer",
    "Flask Developer",
    "Frontend Developer",
    "Frontend Engineer",
    "Front End Developer",
    "Front End Engineer",
    "Full Stack Developer",
    "Full Stack Engineer",
    "Fullstack Developer",
    "Game Developer",
    "GCP Engineer",
    "Generative AI Engineer",
    "Go Developer",
    "Graphic Designer",
    "iOS Developer",
    "Infrastructure Engineer",
    "Integration Specialist",
    "IT Manager",
    "IT Support Specialist",
    "Java Developer",
    "JavaScript Developer",
    "Jenkins Engineer",
    "Kotlin Developer",
    "Kubernetes Engineer",
    "Laravel Developer",
    "LLM Engineer",
    "Machine Learning Engineer",
    "Machine Learning Researcher",
    "Mobile App Developer",
    "Mobile Developer",
    "MongoDB Developer",
    "MySQL Developer",
    "Network Administrator",
    "Network Engineer",
    "NLP Engineer",
    "Node.js Developer",
    "Platform Engineer",
    "PostgreSQL Developer",
    "Power BI Developer",
    "Product Designer",
    "Prompt Engineer",
    "Python Developer",
    "QA Engineer",
    "Quality Assurance Analyst",
    "React Developer",
    "React Native Developer",
    "Redis Developer",
    "Research Scientist",
    "Ruby Developer",
    "Rust Developer",
    "SAP Consultant",
    "Salesforce Developer",
    "Security Analyst",
    "Security Engineer",
    "Site Reliability Engineer",
    "SOC Analyst",
    "Software Developer",
    "Software Development Engineer",
    "Software Engineer",
    "Software Engineer Intern",
    "Solutions Architect",
    "Solution Architect",
    "Spring Developer",
    "SDE",
    "SDET",
    "System Architect",
    "Systems Administrator",
    "Systems Engineer",
    "Tableau Developer",
    "Technical Account Manager",
    "Technical Project Manager",
    "Technical Support Engineer",
    "Technical Writer",
    "Terraform Engineer",
    "TypeScript Developer",
    "UI Designer",
    "UI Engineer",
    "UI/UX Designer",
    "UX Designer",
    "UX Researcher",
    "Vue.js Developer",
    "Web Designer",
    "Web Developer",
  ])
).sort((left, right) => left.localeCompare(right));

export const NON_TECHNICAL_JOB_ROLES = Array.from(
  new Set([
    "Account Executive",
    "Account Manager",
    "Administrative Assistant",
    "Analytics Manager",
    "Art Director",
    "Audit Manager",
    "Audit Specialist",
    "Business Analyst",
    "Business Analyst Intern",
    "Business Development Manager",
    "Career Coach",
    "Change Manager",
    "Chief Marketing Officer",
    "Compliance Officer",
    "Content Marketing Manager",
    "Content Strategist",
    "Contract Administrator",
    "Contract Specialist",
    "Copywriter",
    "Creative Director",
    "Customer Experience Manager",
    "Customer Success Manager",
    "Demand Generation Manager",
    "Digital Marketing Manager",
    "Director of Operations",
    "E-commerce Manager",
    "Employee Relations Specialist",
    "Executive Assistant",
    "Finance Analyst",
    "Finance Manager",
    "Financial Analyst",
    "Financial Modeler",
    "Growth Marketing Manager",
    "HR Business Partner",
    "HR Executive",
    "HR Manager",
    "Human Resources Specialist",
    "Investment Banker",
    "Legal Counsel",
    "Logistics Coordinator",
    "Marketing Analyst",
    "Marketing Coordinator",
    "Marketing Manager",
    "Operations Analyst",
    "Operations Manager",
    "Payroll Specialist",
    "Portfolio Manager",
    "Procurement Manager",
    "Procurement Specialist",
    "Product Analyst",
    "Product Manager",
    "Project Coordinator",
    "Project Manager",
    "Public Policy Analyst",
    "Quality Control Inspector",
    "Real Estate Manager",
    "Recruitment Coordinator",
    "Recruiting Manager",
    "Regulatory Affairs Specialist",
    "Risk Analyst",
    "Sales Associate",
    "Sales Executive",
    "Sales Manager",
    "Sales Operations Analyst",
    "Scrum Master",
    "Service Delivery Manager",
    "Social Media Manager",
    "Supply Chain Analyst",
    "Supply Chain Manager",
    "Talent Acquisition Specialist",
    "Technical Recruiter",
    "Transportation Planner",
    "Urban Planner",
    "Video Producer",
    "Visual Designer",
    "Warehouse Manager",
  ])
).sort((left, right) => left.localeCompare(right));

export const ALL_JOB_ROLE_OPTIONS = Array.from(
  new Set(
    [...JOB_ROLES, ...EXTRA_JOB_ROLE_ALIASES]
      .map((role) => String(role || "").trim())
      .filter(Boolean)
  )
).sort((left, right) => left.localeCompare(right));

export const MOCK_JOB_ROLES = Array.from(new Set(TECHNICAL_JOB_ROLES)).sort((left, right) =>
  left.localeCompare(right)
);

export const CORPORATE_JOB_ROLES = Array.from(
  new Set([
    ...TECHNICAL_JOB_ROLES,
    ...NON_TECHNICAL_JOB_ROLES,
    ...EXTRA_JOB_ROLE_ALIASES,
  ])
).sort((left, right) => left.localeCompare(right));

export function normalizeRoleText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function levenshteinDistance(source, target) {
  const left = normalizeRoleText(source);
  const right = normalizeRoleText(target);
  if (!left) return right.length;
  if (!right) return left.length;

  const matrix = Array.from({ length: left.length + 1 }, (_, rowIndex) =>
    Array.from({ length: right.length + 1 }, (_, columnIndex) =>
      rowIndex === 0 ? columnIndex : columnIndex === 0 ? rowIndex : 0
    )
  );

  for (let row = 1; row <= left.length; row += 1) {
    for (let column = 1; column <= right.length; column += 1) {
      const cost = left[row - 1] === right[column - 1] ? 0 : 1;
      matrix[row][column] = Math.min(
        matrix[row - 1][column] + 1,
        matrix[row][column - 1] + 1,
        matrix[row - 1][column - 1] + cost
      );
    }
  }

  return matrix[left.length][right.length];
}

function scoreRoleMatch(input, option) {
  const normalizedInput = normalizeRoleText(input);
  const normalizedOption = normalizeRoleText(option);
  if (!normalizedInput || !normalizedOption) return 0;
  if (normalizedInput === normalizedOption) return 1000;
  if (normalizedOption.startsWith(normalizedInput)) return 920 - (normalizedOption.length - normalizedInput.length);
  if (normalizedOption.includes(normalizedInput)) return 840 - (normalizedOption.length - normalizedInput.length);

  const inputTokens = normalizedInput.split(" ").filter(Boolean);
  const optionTokens = normalizedOption.split(" ").filter(Boolean);
  const matchedTokens = inputTokens.filter((token) =>
    optionTokens.some(
      (optionToken) =>
        optionToken.startsWith(token) ||
        token.startsWith(optionToken) ||
        levenshteinDistance(token, optionToken) <= 2
    )
  ).length;

  const distance = levenshteinDistance(normalizedInput, normalizedOption);
  return matchedTokens * 120 + Math.max(0, 420 - distance * 18);
}

export function getRoleSuggestions(input, options, limit = 8) {
  const normalizedInput = normalizeRoleText(input);
  if (!normalizedInput) return [];

  return options
    .map((role) => ({ role, score: scoreRoleMatch(normalizedInput, role) }))
    .filter((item) => item.score >= 180)
    .sort((left, right) => {
      if (right.score !== left.score) return right.score - left.score;
      return left.role.localeCompare(right.role);
    })
    .slice(0, limit)
    .map((item) => item.role);
}

export function getResolvedJobRole(input, options) {
  const normalizedInput = normalizeRoleText(input);
  if (!normalizedInput) return "";

  const exactMatch = options.find((role) => normalizeRoleText(role) === normalizedInput);
  if (exactMatch) return exactMatch;

  const [bestMatch] = getRoleSuggestions(input, options, 1);
  if (!bestMatch) return String(input || "").trim();

  return scoreRoleMatch(input, bestMatch) >= 300 ? bestMatch : String(input || "").trim();
}

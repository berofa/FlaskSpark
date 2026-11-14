/**
 * Password strength scoring of Bootstrap 6 (js/src/strength.ts, MIT), without DOM (testable in Node).
 */

export const STRENGTH_LEVELS = ["weak", "fair", "good", "strong"];

export const STRENGTH_DEFAULTS = {
  minLength: 8,
  weights: { minLength: 1, extraLength: 1, lowercase: 1, uppercase: 1, numbers: 1, special: 1, multipleSpecial: 1, longPassword: 1 },
  thresholds: [2, 4, 6], // weak ≤ 2, fair ≤ 4, good ≤ 6, strong above
};

const SPECIAL = /[!@#$%^&*(),.?":{}|<>]/;
const TWO_SPECIAL = /[!@#$%^&*(),.?":{}|<>].*[!@#$%^&*(),.?":{}|<>]/;

/** The score of a password (0 for an empty one); `scorer(password)` replaces the built-in criteria. */
export function scorePassword(password, { minLength = STRENGTH_DEFAULTS.minLength, weights = {}, scorer = null } = {}) {
  if (!password) return 0;
  if (typeof scorer === "function") return scorer(password);
  const w = { ...STRENGTH_DEFAULTS.weights, ...weights };
  let score = 0;
  if (password.length >= minLength) score += w.minLength;
  if (password.length >= minLength + 4) score += w.extraLength;
  if (/[a-z]/.test(password)) score += w.lowercase;
  if (/[A-Z]/.test(password)) score += w.uppercase;
  if (/\d/.test(password)) score += w.numbers;
  if (SPECIAL.test(password)) score += w.special;
  if (TWO_SPECIAL.test(password)) score += w.multipleSpecial;
  if (password.length >= 16) score += w.longPassword;
  return score;
}

/** The level of a score: null (0), "weak", "fair", "good" or "strong". */
export function strengthLevel(score, thresholds = STRENGTH_DEFAULTS.thresholds) {
  if (!score) return null;
  const [weak, fair, good] = thresholds;
  if (score <= weak) return "weak";
  if (score <= fair) return "fair";
  if (score <= good) return "good";
  return "strong";
}

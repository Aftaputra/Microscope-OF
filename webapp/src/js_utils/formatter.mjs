// Generic functions for formatting

/**
 * Format a single number into a human-readable string.
 * Uses exponential notation for very large/small numbers.
 *
 * @param {number} num - The number to format.
 * @param {number} [maxDigits=4] - Maximum number of digits in of the formatted string.
 * @returns {string} - Formatted number as a string.
 */
export function formatNumber(num, maxDigits = 4) {
  if (typeof num !== "number" || isNaN(num)) return String(num);

  // First convert to just a number
  const normal = String(num);
  // Use toPrecision to handle rounding and turnign to exponential
  const rounded = num.toPrecision(maxDigits);

  // Return whichever string is shorter, preventing trailing zeros on decimals
  return rounded.length < normal.length ? rounded : normal;
}

/**
 * Recursively format numbers inside arrays or objects.
 *
 * @param {any} value - Value to format (number, array, object, or other).
 * @param {number} [maxDigits=4] - Maximum number of digits in each number of the formatted string.
 * @returns {string} - A formatted display string.
 */
export function formatValue(value, maxDigits = 4) {
  if (Array.isArray(value)) {
    const items = value.map((val) => formatValue(val, maxDigits));
    return `[${items.join(", ")}]`;
  }
  if (typeof value === "object" && value !== null) {
    const entries = Object.entries(value).map(([key, val]) => {
      return `${key}: ${formatValue(val, maxDigits)}`;
    });
    return `{${entries.join(", ")}}`;
  }

  // Attempt to coerce to number as numbers in input boxes may be represented as strings
  let asNum = Number(value);
  if (!Number.isNaN(asNum)) {
    return formatNumber(asNum, maxDigits);
  }
  // Only if the string will not coerce to a number do we output the value.
  return value;
}

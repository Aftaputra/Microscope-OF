import { vi, beforeEach, afterEach } from "vitest";

let consoleWatchdog;

// Create an isolated, in-memory mock for localStorage

const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = value.toString();
    },
    removeItem: (key) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

// Override Node's native localStorage
vi.stubGlobal("localStorage", localStorageMock);

// Clean up
beforeEach(() => {
  localStorage.clear();
  consoleWatchdog = vi.spyOn(console, "warn");
});

afterEach(({ task }) => {
  if (!consoleWatchdog) return;

  // Grab all warnings
  const warnings = consoleWatchdog.mock.calls;

  // Clean up the spy so it doesn't leak
  consoleWatchdog.mockRestore();

  // Filter specifically for Vue warnings
  const vueWarnings = warnings.filter(
    (args) => typeof args[0] === "string" && args[0].includes("[Vue warn]"),
  );

  // If Vue has warns forcefully fail this test block --max-warnings=0
  if (vueWarnings.length > 0) {
    const warningMessages = vueWarnings.map((args) => args.join(" ")).join("\n\n");

    // Throw a plain string instead of using expect.fail() or new Error()!
    // Without an Error object, there is no stack trace, so Vitest CANNOT show a code snippet.
    throw `[Vue warn] Failure in "${task.name}":\n\n${warningMessages}`;
  }
});

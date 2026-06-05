import { vi, beforeEach } from "vitest";

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
});

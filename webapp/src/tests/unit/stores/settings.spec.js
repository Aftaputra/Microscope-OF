import { setActivePinia, createPinia } from "pinia";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { useSettingsStore } from "../../../stores/settings";

describe("Settings Store", () => {
  beforeEach(() => {
    // Mock the browser's window.location BEFORE the store initializes
    // This prevents the getOriginFromLocation() function from crashing.
    vi.stubGlobal("location", {
      // The following baseUri is arbitrarily set
      href: "http://microscope-test.local:5000/",
    });

    // Create a fresh Pinia instance for every single test
    // This guarantees state doesn't leak between the 'it' blocks.
    setActivePinia(createPinia());
  });

  describe("Initialization", () => {
    it("parses the baseUri correctly from window.location", () => {
      const store = useSettingsStore();
      // It should extract the origin and append /api/v3
      expect(store.baseUri).toBe("http://microscope-test.local:5000/api/v3");
    });

    it("initializes with correct default state", () => {
      const store = useSettingsStore();
      expect(store.ready).toBe(false);
      expect(store.waiting).toBe(false);
      expect(store.appTheme).toBe("system");
      expect(store.activeStreams).toEqual({});
    });
  });

  describe("Actions", () => {
    it("setConnected() updates waiting and ready states", () => {
      const store = useSettingsStore();

      // Mutate state to ensure setConnected overrides it
      store.waiting = true;
      store.ready = false;

      store.setConnected();

      expect(store.waiting).toBe(false);
      expect(store.ready).toBe(true);
    });

    it("resetState() clears connection status and sets error", () => {
      const store = useSettingsStore();

      // Mutate state
      store.waiting = true;
      store.ready = true;
      store.error = "";

      store.resetState();

      expect(store.waiting).toBe(false);
      expect(store.ready).toBe(false);
      expect(store.error).toBe("Microscope is not connected.");
    });

    it("addStream() adds a stream ID to activeStreams", () => {
      const store = useSettingsStore();

      store.addStream("mjpeg_stream");

      expect(store.activeStreams["mjpeg_stream"]).toBe(true);
    });

    it("removeStream() sets a stream ID to false in activeStreams", () => {
      const store = useSettingsStore();

      // Setup initial state
      store.activeStreams = { mjpeg_stream: true };

      store.removeStream("mjpeg_stream");

      expect(store.activeStreams["mjpeg_stream"]).toBe(false);
    });
  });
});

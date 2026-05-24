import { shallowMount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { createTestingPinia } from "@pinia/testing";
import { setActivePinia } from "pinia";
import axios from "axios";
import fs from "fs";
import path from "path";
import LoggingContent from "../../components/tabContentComponents/loggingContent.vue";

// Mock Axios
vi.mock("axios", () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      patch: vi.fn(),
    },
  };
});

// Mock VueUse to prevent IntersectionObserver crashes in JSDOM
// This will be removed once vue-route is implemented
vi.mock("@vueuse/core", () => ({
  useIntersectionObserver: vi.fn(() => ({
    stop: vi.fn(),
  })),
}));

// Test Description
describe("Test LoggingContent.vue", () => {
  let wrapper;

  // Define path to a real log file and read it
  const logFilePath = path.resolve(__dirname, "../fixtures/realLog.txt");
  const mockLogData = fs.readFileSync(logFilePath, "utf-8");

  // Things to do before each test
  beforeEach(async () => {
    vi.useFakeTimers();
    // Reset mocks before each test
    vi.resetAllMocks();

    // Set axios to return our fake logs
    axios.get.mockResolvedValue({ data: mockLogData });

    // Mount the component with a fake Pinia store
    wrapper = shallowMount(LoggingContent, {
      attachTo: document.body,
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              settings: { baseUri: "http://microscope.local:5000/api/v3" },
            },
          }),
        ],
        // Simplify child components
        stubs: {
          PaginateLinks: true,
          EndpointButton: true,
          transition: true,
          teleport: true,
          settings: true,
        },
      },
    });
    // flush so we avoid leaving uncompleted processes running on background
    await flushPromises();
    vi.advanceTimersByTime(1000);
    vi.useRealTimers();
  });

  // Tear down wrapper, unmount testing component
  afterEach(() => {
    if (wrapper) {
      wrapper.unmount(); // Clean up virtual DOM and memory bindings
    }
    setActivePinia(undefined);
    document.body.innerHTML = "";

    if (global.gc) {
      global.gc(); // Forces V8 engine to immediately run Garbage Collection
    }
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  // Test 1: Render check, if things do exist in the page as intended
  it("renders the component correctly", async () => {
    // Check if component is been loaded and it is rendered
    expect(wrapper.exists()).toBe(true);
    // Check if navbar exists
    expect(wrapper.find(".logging-navbar").exists()).toBe(true);
  });

  // Test 2: Check log parsing to see if specific INFO exists
  it("fetches logs and parses them correctly when updateLogs is called", async () => {
    // Trigger the method
    await wrapper.vm.updateLogs();
    await flushPromises();

    // Verify Axios was called with the correct URI from the Pinia store
    expect(axios.get).toHaveBeenCalledWith("http://microscope.local:5000/api/v3/log/");

    // Verify the logs have correct file length
    // Helps validate formatting, etc
    expect(wrapper.vm.logs.length).toBe(5491);

    // Check the most recent log
    expect(wrapper.vm.logs[0].level).toBe("INFO");

    // Check if the multi-line file has real first connection information
    expect(wrapper.vm.logs[0].message).toContain("uvicorn");
    expect(wrapper.vm.logs[0].summary).toContain("http://0.0.0.0:5000");
  });

  // Test 3: Filter logging file information
  it("filters logs based on the selected level", async () => {
    await wrapper.vm.updateLogs();

    // Set filter to WARNING wait and compare expected length
    wrapper.vm.filterLevel = "WARNING";
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.filteredItems.length).toBe(1449);
    expect(wrapper.vm.filteredItems[0].level).toBe("WARNING");

    // Set filter to INFO wait and compare expected length
    wrapper.vm.filterLevel = "INFO";
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.filteredItems.length).toBe(5491);
    expect(wrapper.vm.filteredItems[0].level).toBe("INFO");

    // Set filter to ERROR wait and compare expected length
    wrapper.vm.filterLevel = "ERROR";
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.filteredItems.length).toBe(7);
    expect(wrapper.vm.filteredItems[0].level).toBe("ERROR");
  });

  // Test 4: Click buttons
  // This required the component file to be modified by adding data-test-id flags.
  // Flags are needed as classes and text content may change by translation or style change.
  it("click buttons", async () => {
    // Click download button
    const downloadButton = wrapper.find('[data-test-id="download-btn"]');
    expect(downloadButton.exists()).toBe(true);
    await downloadButton.trigger("click");

    // Click update button
    const updateButton = wrapper.find('[data-test-id="update-btn"]');
    expect(updateButton.exists()).toBe(true);
    await updateButton.trigger("click");
  });

  // Prevents Vitest "Async Leak" errors by giving Vue's internal
  // DevTools timer a few milliseconds to finish before teardown.
  afterAll(async () => {
    await new Promise((resolve) => setTimeout(resolve, 15));
  });
});

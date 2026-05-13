import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { createTestingPinia } from "@pinia/testing";
import axios from "axios";
import LoggingContent from "../../components/tabContentComponents/loggingContent.vue";

// Mock Axios
vi.mock("axios");

// Mock VueUse to prevent IntersectionObserver crashes in JSDOM
vi.mock("@vueuse/core", () => ({
  useIntersectionObserver: vi.fn(),
}));

describe("LoggingContent.vue", () => {
  let wrapper;

  // A sample log string matching backend's format
  const mockLogData = `[2023-10-27T10:00:00.000Z] [INFO] System started successfully
[2023-10-27T10:01:00.000Z] [WARNING] Temperature is rising
[2023-10-27T10:02:00.000Z] [ERROR] Traceback (most recent call last):
  File "main.py", line 10, in <module>
    connect()`;

  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();

    // Set axios to return our fake logs
    axios.get.mockResolvedValue({ data: mockLogData });

    // Mount the component with a fake Pinia store
    wrapper = mount(LoggingContent, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              settings: { baseUri: "http://localhost:3000/api/v3" },
            },
          }),
        ],
        // Simplify child components
        stubs: ["PaginateLinks", "EndpointButton"],
      },
    });
  });

  // Render check
  it("renders the component correctly", () => {
    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find(".logging-navbar").exists()).toBe(true);
  });

  it("fetches logs and parses them correctly when updateLogs is called", async () => {
    // Trigger the method
    await wrapper.vm.updateLogs();

    // Verify Axios was called with the correct URI from the Pinia store
    expect(axios.get).toHaveBeenCalledWith("http://localhost:3000/api/v3/log/");

    // Verify the logs array was populated and reversed (newest first)
    expect(wrapper.vm.logs.length).toBe(3);

    // Check if the most recent log (ERROR) is first due to .reverse()
    expect(wrapper.vm.logs[0].level).toBe("ERROR");

    // Check if the multi-line traceback was appended correctly to the ERROR log
    expect(wrapper.vm.logs[0].message).toContain("Traceback");
    expect(wrapper.vm.logs[0].summary).toContain("connect()");
  });

  it("filters logs based on the selected level", async () => {
    await wrapper.vm.updateLogs();

    // Set filter to ERROR (should only show ERROR and CRITICAL)
    wrapper.vm.filterLevel = "ERROR";

    // wait for Vue reactivity to update computed properties
    await wrapper.vm.$nextTick();

    // Only the 1 ERROR log should remain in filteredItems
    expect(wrapper.vm.filteredItems.length).toBe(1);
    expect(wrapper.vm.filteredItems[0].level).toBe("ERROR");
  });
});

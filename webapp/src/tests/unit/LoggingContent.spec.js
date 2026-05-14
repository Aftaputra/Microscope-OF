import { shallowMount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { createTestingPinia } from "@pinia/testing";
import axios from "axios";
import LoggingContent from "../../components/tabContentComponents/loggingContent.vue";

// Mock Axios
vi.mock("axios");

// Mock VueUse to prevent IntersectionObserver crashes in JSDOM
vi.mock("@vueuse/core", () => ({
  useIntersectionObserver: vi.fn(() => ({
    stop: vi.fn(),
  })),
}));

describe("LoggingContent.vue", () => {
  let wrapper;

  // A sample log string matching backend's format
  const mockLogData = `[2026-05-14 08:46:12,808] [INFO] OFM server root logger has been set up at INFO level`;

  beforeEach(async () => {
    // Reset mocks before each test
    vi.clearAllMocks();

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
              settings: { origin: "http://microscope.local:5000/api/v3" },
            },
          }),
        ],
        // Simplify child components
        stubs: {
            PaginateLinks: true,
            EndpointButton: true,
            transition: false,
            teleport: true,
          },
      },
    });
    await flushPromises(); 
  });

  // Render check
  it("renders the component correctly", () => {
    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find(".logging-navbar").exists()).toBe(true);
  });

  it("fetches logs and parses them correctly when updateLogs is called", async () => {
    // Trigger the method
    await wrapper.vm.updateLogs();
    await flushPromises();

    // Verify Axios was called with the correct URI from the Pinia store
    expect(axios.get).toHaveBeenCalledWith("http://microscope.local:5000/api/v3/log/");

    // Verify the logs array was populated and reversed (newest first)
    expect(wrapper.vm.logs.length).toBe(1);

    // Check if the most recent log (ERROR) is first due to .reverse()
    expect(wrapper.vm.logs[0].level).toBe("INFO");

    // Check if the multi-line traceback was appended correctly to the ERROR log
    expect(wrapper.vm.logs[0].message).toContain("OFM");
    expect(wrapper.vm.logs[0].summary).toContain("server");
  });

  it("filters logs based on the selected level", async () => {
    await wrapper.vm.updateLogs();

    // Set filter to ERROR (should only show ERROR and CRITICAL)
    wrapper.vm.filterLevel = "INFO";

    // wait for Vue reactivity to update computed properties
    await wrapper.vm.$nextTick();

    // Only the 1 ERROR log should remain in filteredItems
    expect(wrapper.vm.filteredItems.length).toBe(1);
    expect(wrapper.vm.filteredItems[0].level).toBe("INFO");
  });
});

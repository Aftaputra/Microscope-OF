import { describe, it, expect, beforeEach, afterEach, afterAll, vi } from "vitest";
import { shallowMount, flushPromises } from "@vue/test-utils";
import { createTestingPinia } from "@pinia/testing";
import { markRaw } from "vue";

// Eagerly import ALL .vue files at the components directory
// Except the ones inside experimental
const componentModules = Object.fromEntries(
  Object.entries(import.meta.glob("../../components/**/*.vue", { eager: true })),
);
// Skip list, add here components that have their own test spec.js file
const skipList = ["loggingContent.vue"];

// Map filenames to the specific props or mocks required
// Not all components ask for props
const componentOverrides = {
  "serverSpecifiedPropertyControl.vue": {
    props: {
      propertyData: {},
      propertyName: "",
      thingName: "",
    },
    global: {
      mocks: {
        wotStore: {
          thingDescriptions: {
            test_thing: {
              properties: {
                property_1: {},
                fancy_property_2: {},
              },
            },
          },
        },
      },
    },
  },

  "slideScanContent.vue": {
    global: {
      mocks: {
        wotStore: {
          thingDescriptions: {
            test_thing: {
              properties: {
                fancy_property_1: {},
                fancy_property_2: {},
              },
            },
          },
        },
      },
    },
  },

  "slideScanControls.vue": {
    global: {
      mocks: {
        wotStore: {
          thingDescriptions: {
            test_thing: {
              properties: {
                fancy_property_1: {},
                fancy_property_2: {},
              },
            },
          },
        },
      },
    },
  },

  "miniStreamDisplay.vue": {
    props: { streamId: "testProp" },
  },
  "streamContent.vue": {
    props: { streamId: "testProp" },
  },
  "paginateLinks.vue": {
    props: { totalPages: 5, currentPage: 1 },
  },
  "simpleAccordion.vue": {
    props: { title: "Test Accordion Title" },
  },
  "tabContent.vue": {
    props: { tabID: "tab-1", currentTab: "tab-1" },
  },
  "tabIcon.vue": {
    props: { tabID: "tab-1", currentTab: "tab-1" },
  },
  "actionButton.vue": {
    props: { action: "test-action", thing: "test-thing" },
  },
  "actionLogDisplay.vue": {
    props: { taskStatus: "", log: [] },
  },
  "endActionButton.vue": {
    props: { url: "http://microscope.local/api/v3" },
  },
  "endpointButton.vue": {
    props: { url: "http://microscope.local/api/v3" },
  },
  "matrixDisplay.vue": {
    props: { matrix: [] },
  },
  "actionProgressBar.vue": {
    props: { taskStatus: "" },
  },
  "actionStatusModal.vue": {
    props: {
      title: "",
      log: [],
      canTerminate: true,
      taskRunning: true,
      taskStarted: true,
      taskStatus: "",
    },
  },
  "inputFromSchema.vue": {
    props: { dataSchema: {} },
  },

  "propertyControl.vue": {
    props: {
      propertyName: "",
      thingName: "test_thing",
      dataSchema: {},
    },

    mocks: {
      wotStore: {
        thingDescriptions: {
          test_thing: {
            actions: {},
            properties: {},
          },
        },
      },
    },
  },
  "serverSpecifiedActionButton.vue": {
    props: {
      actionData: {},
      elements: {},
      propertyData: {},
      action: "test-action",
      thing: "test-thing",
    },
  },
  "serverSpecifiedInterface.vue": {
    props: { elements: [] },
  },
  "calibrationWizardTask.vue": {
    props: { steps: [] },
  },
  "singleStepTask.vue": {
    props: {
      stepComponent: markRaw({ template: '<div class="dummy"></div>' }),
    },
  },
  "actionTab.vue": {
    props: {
      action: "test-action",
      thing: "test-thing",
      taskId: "",
      taskUrl: "",
    },
  },
  "galleryCard.vue": {
    props: { itemData: {} },
  },
  "openSeadragonViewer.vue": {
    props: {
      src: "",
      brightness: 0,
      contrast: 0,
      saturation: 0,
    },
  },
  "cameraCalibrationSettings.vue": {
    props: { cameraUri: "" },
  },

  "galleryContent.vue": {
    global: {
      mocks: {
        readThingProperty: vi.fn(() => []),
      },
    },
  },

  "CSMCalibrationSettings.vue": {
    global: {
      mocks: {
        thingDescriptions: {
          csm: {
            actions: {},
          },
        },
      },
    },
  },
};

describe("Automated Component Smoke Tests", () => {
  // Declare wrapper at this scope so afterEach can clean it up
  let wrapper;

  beforeEach(() => {
    // Environment setup
    vi.useFakeTimers();
    vi.resetAllMocks();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
      wrapper = null;
    }

    // Clean up virtual DOM and memory bindings
    document.body.innerHTML = "";

    // Forces V8 engine to immediately run Garbage Collection
    if (global.gc) {
      global.gc();
    }

    vi.clearAllTimers();
    vi.useRealTimers();
  });

  afterAll(async () => {
    await new Promise((resolve) => setTimeout(resolve, 15));
  });

  // Loop through the file paths
  for (const path in componentModules) {
    const component = componentModules[path].default;
    const fileName = path.split("/").pop();
    const isSkipped = skipList.includes(fileName) || path.toLowerCase().includes("experimental");

    // This check skips vue files that are corrupted or have no meta content
    // .default has meta content even without explicit default export
    // This check serves the purpose to avoid a file halting a CI pipeline
    if (!component) {
      console.error(component);
      // Generate a test specifically to report this failure to Vitest
      it(`${fileName} has a default export`, () => {
        expect.fail(
          `Test Generation Failed: No content in "${fileName}". ` +
            `Please fix this file or add it to the skipList.`,
        );
      });

      // Skip generating the REST of the test suite for this broken file
      return;
    }

    // Dynamically assign the test runner (it.skip if in the list, otherwise standard it)
    const testRunner = isSkipped ? it.skip : it;

    // Run the test
    testRunner(`Shallow mounts ${fileName} without crashing`, async () => {
      // Look up the specific config for this file, default to an empty object
      const override = componentOverrides[fileName] || {};

      wrapper = shallowMount(component, {
        attachTo: document.body,

        // Inject the specific props here!
        props: override.props || {},

        global: {
          plugins: [
            createTestingPinia({
              createSpy: vi.fn,
              // Inject the specific state if it exists, otherwise use empty object
              initialState: override.initialState || {},
            }),
          ],
          stubs: {},
          mocks: {
            // These mocks come from MIXINS
            thingActionAvailable: vi.fn(() => true),
            readThingProperty: vi.fn(() => ({})),
            thingAvailable: vi.fn(() => ({})),
            thingDescription: vi.fn(() => ({
              actions: {},
              properties: {},
            })),
            getOngoingAction: vi.fn(() => Promise.resolve()),
            getThingEndpoint: vi.fn(() => Promise.resolve([])),
            modalError: "",
            ...(override.global?.mocks || {}),
            ...(override.mocks || {}),
          },
        },
      });

      await flushPromises();
      vi.advanceTimersByTime(200);
      expect(wrapper.exists()).toBe(true);
    });
  }
});

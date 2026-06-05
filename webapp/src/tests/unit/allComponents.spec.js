import { describe, it, expect, beforeEach, afterEach, afterAll, vi } from "vitest";
import { shallowMount, flushPromises } from "@vue/test-utils";
import { createTestingPinia } from "@pinia/testing";

// Eagerly import ALL .vue files at the components directory
const componentModules = import.meta.glob("../../components/**/*.vue", { eager: true });

// Skip list, for components that have their own test spec.js file
const skipList = ["loggingContent.vue"];

// Map filenames to the specific props or mocks required
// Not all components ask for props
const componentOverrides = {
  "paginateLinks.vue": {
    props: {
      totalPages: 5,
      currentPage: 1,
    },
  },
  "simpleAccordion.vue": {
    props: { title: "Test Accordion Title" },
  },
  "tabContent.vue": {
    props: {
      tabID: "tab-1",
      currentTab: "tab-1",
    },
  },
  "tabIcon.vue": {
    props: {
      tabID: "tab-1",
      currentTab: "tab-1",
    },
  },
  "actionButton.vue": {
    props: {
      action: "test-action",
      thing: "test-thing",
    },
  },
  "actionLogDisplay.vue": {
    props: {
      taskStatus: "",
      log: [],
    },
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
    props: {
      dataSchema: {},
    },
  },
  "propertyControl.vue": {
    props: {
      propertyName: "",
      thingName: "",
      dataSchema: {},
    },
    mocks: {
      wotStore: {
        thingDescriptions: {
          actions: {},
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
    props: {
      elements: [],
    },
  },
  "serverSpecifiedPropertyControl.vue": {
    props: {
      propertyData: {},
      propertyName: "",
      thingName: "",
    },
  },
  "calibrationWizardTask.vue": {
    props: {
      steps: [],
    },
  },
  "singleStepTask.vue": {
    props: {
      stepComponent: {},
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
    props: {
      itemData: {},
    },
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
    props: {
      cameraUri: "",
    },
  },
  "galleryContent.vue": {
    mocks: {
      readThingProperty: vi.fn(() => []),
    },
  },
  "CSMCalibrationSettings.vue": {
    mocks: {
      thingDescriptions: {
        csm: {
          actions: {},
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
    const isSkipped = skipList.includes(fileName);

    if (!component) return;

    // Dynamically assign the test runner (it.skip if in the list, otherwise standard it)
    const testRunner = isSkipped ? it.skip : it;

    // Run the test
    testRunner(`shallow mounts ${fileName} without crashing`, async () => {
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
            // These values come from MIXINS
            thingActionAvailable: vi.fn(() => true),
            readThingProperty: vi.fn(() => ({})),
            thingAvailable: vi.fn(() => ({})),
            thingDescription: vi.fn(() => ({
              actions: {},
              properties: {},
            })),
            thingDescriptions: vi.fn(() => ({})),
            getOngoingAction: vi.fn(() => Promise.resolve()),
            getThingEndpoint: vi.fn(() => Promise.resolve([])),
            modalError: "",
            ...(override.mocks || {}),
          },
        },
      });

      await flushPromises();
      vi.advanceTimersByTime(1000);
      expect(wrapper.exists()).toBe(true);
    });
  }
});

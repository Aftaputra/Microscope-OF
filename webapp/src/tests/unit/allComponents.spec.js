import { describe, it, expect, beforeEach, afterEach, afterAll, vi } from "vitest";
import { shallowMount, flushPromises } from "@vue/test-utils";
import { createTestingPinia } from "@pinia/testing";
import { markRaw } from "vue";

/**
 * @file Automated component smoke testing suite.
 * @description Iterates through all project components and performs a
 * shallow mount on each. This acts as a first line of defense to catch
 * fatal DOM runtime errors, missing dependencies, or script crashes
 * before they reach production.
 */

/** * Vite eagerly grabs all .vue components, explicitly excluding the experimental folder.
 * * @type {Record<string, { default: any }>} A dictionary mapping file paths to their Vue component modules.
 */
const componentModules = import.meta.glob(
  ["../../components/**/*.vue", "!../../components/experimental/**/*.vue"],
  { eager: true },
);

/**
 * IMPORTANT
 * Skip list, add here components that have their own test .spec.js file
 * */
const skipList = ["loggingContent.vue"];

/**
 * Map filenames to the specific props or mocks required
 * Not all components ask for props
 * If a component has unmet props or global mocks setup.js is set to fail the test
 **/
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
                test_property_1: {},
                test_property_2: {},
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
                test_property_1: {},
                test_property_2: {},
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
                test_property_1: {},
                test_property_2: {},
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

/**
 * Test description this is a fast unit test
 * The objective of this testing is find early
 * component loading issues like bad component setups
 */

describe("Unit Test", () => {
  let wrapper;

  /**
   * Environment setup
   * set Fake timers and Mocks
   */
  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetAllMocks();
  });

  /**
   * Clean up after every single test
   * Unmounts any present component wrapper=
   * Clean up virtual DOM and memory bindings
   * Forces V8 engine to immediately run Garbage Collection
   * clears out timers to avoid leaks
   */
  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
      wrapper = null;
    }

    document.body.innerHTML = "";

    if (global.gc) {
      global.gc();
    }

    vi.clearAllTimers();
    vi.useRealTimers();
  });

  afterAll(async () => {
    await new Promise((resolve) => setTimeout(resolve, 15));
  });

  /**
   * Loop through the file paths
   * Unwraps the component and exposes its definition using ".default"
   * Includes meta information like name, props, components, methods.
   * Do not confuse with export default from script component section
   * Skips components at the skipList from files that are explicitly skipped
   * Also skips components which name starts with the word "experimental"
   * allowing to work with edge case components if needed
   * is discouraged to push components that won't pass a smoke test
   * */
  for (const path in componentModules) {
    const component = componentModules[path].default;
    const fileName = path.split("/").pop();
    const isSkipped = skipList.includes(fileName) || path.toLowerCase().includes("experimental");

    /**
     * This check skips vue files that are corrupted or have no meta content
     * return is preferred as a wrong path in file could lead to halt on CI pipeline or over verbose output
     * An error here means a wrong path or file access error
     * This was needed during the writing of this script
     * Leaving for other future edge cases usage
     * This fails the overall test
     * */
    if (!component || undefined) {
      console.error(component);

      const errorName = fileName + "Wrong Path";

      it(`${errorName} has no correct Path`, () => {
        expect.fail(`Incorrect Path parsing for "${fileName}"`);
      });

      return;
    }

    /**
     * Dynamically assign the test runner (it.skip if in the list, otherwise standard it)
     * Run the test
     * Look up the specific config for this file, default to an empty object
     * Override specific props
     * Inject the specific state if it exists, otherwise use empty object
     * Mocks values come from MIXINS
     */
    const testRunner = isSkipped ? it.skip : it;

    testRunner(`Shallow mounts ${fileName} without crashing`, async () => {
      const override = componentOverrides[fileName] || {};

      wrapper = shallowMount(component, {
        attachTo: document.body,

        props: override.props || {},

        global: {
          plugins: [
            createTestingPinia({
              createSpy: vi.fn,
              initialState: override.initialState || {},
            }),
          ],
          stubs: {},
          mocks: {
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

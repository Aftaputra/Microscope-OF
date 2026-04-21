import { createStore } from "vuex";
import wotStoreModule from "./wot-client";

function getOriginFromLocation() {
  // This will default to the same origin that's serving
  // the web app - but can be overridden by the URL.
  // See also devTools.vue which can change the origin.
  let url = new URL(window.location.href);
  let origin = url.searchParams.get("overrideOrigin");
  if (origin) {
    return origin;
  } else {
    return url.origin;
  }
}

/**
 * Converts a Vuex state key (e.g. "appTheme") into a corresponding
 * Vuex mutation name (e.g. "changeAppTheme") using the `change<Key>`
 * convention.
 *
 * @param {string} key - The Vuex state key to convert.
 * @returns {string} - The formatted mutation name.
 */
function keyToMutationName(key) {
  return `change${key.charAt(0).toUpperCase() + key.slice(1)}`;
}

/**
 * Converts a Vuex mutation name (e.g. "changeAppTheme") back into
 * the corresponding state key (e.g. "appTheme") using the
 * `change<Key>` convention.
 *
 * @param {string} mutationName - The Vuex mutation name to reverse.
 * @returns {string|null} - The derived state key, or null if the
 *     mutation name doesn't match the `change<Key>` convention.
 */
function mutationToKey(mutationName) {
  const prefix = "change";
  if (!mutationName.startsWith(prefix)) {
    return null; // Not a mutation we care about
  }
  const key = mutationName.slice(prefix.length);
  return key.charAt(0).toLowerCase() + key.slice(1);
}

const LOCALSTORAGE_KEYS = [
  "appTheme",
  "disableStream",
  "overrideOrigin",
  "navigationStepSize",
  "navigationInvert",
];

export default createStore({
  modules: {
    wot: wotStoreModule,
  },
  state: {
    origin: getOriginFromLocation(),
    available: false,
    waiting: false,
    error: "",
    trackWindow: true,
    activeStreams: {},
    microscopeHostname: "",
    // Persistent items:
    // The app theme (e.g. light/dark)
    appTheme: "system",
    disableStream: false,
    // The origin to use if overriding with dev tools
    overrideOrigin: "http://microscope.local:5000",
    // The step sizes for navigation via control pane/keys presses
    navigationStepSize: {
      x: 200,
      y: 200,
      z: 50,
    },
    // The axis inversion for navigation via control pane/keys presses
    navigationInvert: {
      x: false,
      y: false,
      z: false,
    },
  },

  mutations: {
    changeOrigin(state, origin) {
      state.origin = origin;
    },
    changeWaiting(state, waiting) {
      state.waiting = waiting;
    },
    changeDisableStream(state, disabled) {
      state.disableStream = disabled;
    },
    changeTrackWindow(state, enabled) {
      state.trackWindow = enabled;
    },
    changeAppTheme(state, theme) {
      state.appTheme = theme;
    },
    resetState(state) {
      state.waiting = false;
      state.available = false;
      state.error = null;
    },
    setConnected(state) {
      state.waiting = false;
      state.available = true;
    },
    setErrorMessage(state, msg) {
      state.error = msg;
    },
    addStream(state, id) {
      state.activeStreams[id] = true;
    },
    removeStream(state, id) {
      state.activeStreams[id] = false;
    },
    changeMicroscopeHostname(state, value) {
      state.microscopeHostname = value;
    },
    changeOverrideOrigin(state, value) {
      state.overrideOrigin = value;
    },
    changeNavigationStepSize(state, value) {
      state.navigationStepSize = value;
    },
    changeNavigationInvert(state, value) {
      state.navigationInvert = value;
    },
  },

  actions: {},

  getters: {
    baseUri: (state) => state.origin,
    ready: (state) => state.available,
  },

  plugins: [
    (store) => {
      // Load initial state from localStorage
      LOCALSTORAGE_KEYS.forEach((key) => {
        const saved = localStorage.getItem(key);
        if (saved !== null) {
          try {
            const parsed = JSON.parse(saved);
            const mutationName = keyToMutationName(key);
            store.commit(mutationName, parsed);
          } catch (e) {
            console.warn(`Failed to parse localStorage key "${key}":`, e);
            localStorage.removeItem(key);
          }
        }
      });

      // Subscribe to mutations
      store.subscribe((mutation, state) => {
        const key = mutationToKey(mutation.type);
        // If the mutation is chacning a local storage key then update localStorage
        if (key && LOCALSTORAGE_KEYS.includes(key)) {
          localStorage.setItem(key, JSON.stringify(state[key]));
        }
      });
    },
  ],
});

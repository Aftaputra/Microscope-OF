import Vue from "vue";
import Vuex from "vuex";
import wotStoreModule from "./wot-client";

Vue.use(Vuex);

const LOCALSTORAGE_KEYS = ["appTheme"];

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

export default new Vuex.Store({
  modules: {
    wot: wotStoreModule,
  },
  state: {
    origin: getOriginFromLocation(),
    available: false,
    waiting: false,
    error: "",
    disableStream: false,
    autoGpuPreview: false,
    trackWindow: true,
    galleryEnabled: true,
    appTheme: "system",
    activeStreams: {},
    microscopeHostname: "",
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
    changeAutoGpuPreview(state, enabled) {
      state.autoGpuPreview = enabled;
    },
    changeTrackWindow(state, enabled) {
      state.trackWindow = enabled;
    },
    changeAppTheme(state, theme) {
      state.appTheme = theme;
    },
    changeGalleryEnabled(state, enabled) {
      state.galleryEnabled = enabled;
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
  },

  actions: {},

  getters: {
    baseUri: state => state.origin,
    ready: state => state.available,
  },

  plugins: [
    store => {
      // Load initial state from localStorage
      LOCALSTORAGE_KEYS.forEach(key => {
        const saved = localStorage.getItem(key);
        if (saved !== null) {
          const mutationName = keyToMutationName(key);
          store.commit(mutationName, JSON.parse(saved));
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

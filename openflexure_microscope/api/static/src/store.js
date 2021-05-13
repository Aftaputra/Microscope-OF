import Vue from "vue";
import Vuex from "vuex";

Vue.use(Vuex);

const moduleImjoy = {
  namespaced: true,
  state: () => ({
    tabs: [],
    openImageMenu: [],
    openScanMenu: []
  }),
  mutations: {
    addOpenImageItem(state, newItem) {
      state.openImageMenu.push(newItem);
    }, // TODO: add a mutation to remove items when plugins are unloaded
    addOpenScanItem(state, newItem) {
      state.openScanMenu.push(newItem);
    }, // TODO: add a mutation to remove items when plugins are unloaded
    clearMenus(state) {
      // This is primarily useful to reset the state in hot-reloads of
      // imjoyContent.vue
      state.openImageMenu = [];
      state.openScanMenu = [];
    },
    addTab(state, newItem) {
      // Add a tab to the list of ImJoy tabs
      state.tabs.push(newItem);
    },
    removeTab(state, tabToRemove) {
      const index = state.tabs.indexOf(tabToRemove);
      if (index > -1) {
        state.tabs.splice(index, 1);
      } else {
        console.warn(
          `Attempted to remove a non-existing ImJoy tab ${tabToRemove}`
        );
      }
    },
    /**
     * Set a parameter on any matching tab objects
     */
    setTabProperty(state, payload) {
      let tab = payload.tab;
      let key = payload.key;
      let value = payload.value;
      for (let i = 0; i < state.tabs.length; i++) {
        let t = state.tabs[i];
        if ((t === tab) | (t.name === tab) | (t.id === tab)) {
          t[key] = value;
        }
        state.tabs.splice(i, 1, t); // This should work nicely with reactive stuff
      }
      //state.tabs = tablist; // This should force an update
    }
  },
  actions: {},
  getters: {}
};

export default new Vuex.Store({
  modules: {
    imjoy: moduleImjoy
  },
  state: {
    origin: window.location.origin,
    available: false,
    waiting: false,
    error: "",
    disableStream: false,
    autoGpuPreview: false,
    trackWindow: true,
    IHIEnabled: false,
    appTheme: "system",
    activeStreams: {}
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
    changeIHIEnabled(state, enabled) {
      state.IHIEnabled = enabled;
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
    }
  },

  actions: {},

  getters: {
    uriV2: state => `${state.origin}/api/v2`,
    baseUri: state => state.origin,
    ready: state => state.available
  }
});

import Vue from "vue";
import Vuex from "vuex";

Vue.use(Vuex);

export default new Vuex.Store({
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
    activeStreams: {},
    openInImjoyMenuItems: [],
    openScanInImjoyMenuItems: []
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
    },
    addOpenInImjoyMenuItem(state, newItem) {
      state.openInImjoyMenuItems.push(newItem);
    }, // TODO: add a mutation to remove items when plugins are unloaded
    addOpenScanInImjoyMenuItem(state, newItem) {
      state.openScanInImjoyMenuItems.push(newItem);
    } // TODO: add a mutation to remove items when plugins are unloaded
  },

  actions: {},

  getters: {
    uriV2: state => `${state.origin}/api/v2`,
    baseUri: state => state.origin,
    ready: state => state.available
  }
});

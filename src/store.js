import Vue from "vue";
import Vuex from "vuex";

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    host: "",
    port: 5000,
    available: false,
    waiting: false,
    error: "",
    globalSettings: {
      disableStream: false,
      autoGpuPreview: false,
      trackWindow: true,
      appTheme: "system"
    }
  },

  mutations: {
    changeHost(state, [host, port]) {
      state.host = host;
      state.port = port;
    },
    changeWaiting(state, waiting) {
      state.waiting = waiting;
    },
    changeSetting(state, [key, value]) {
      state.globalSettings[key] = value;
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
    setError(state, msg) {
      state.waiting = false;
      state.error = msg;
    }
  },

  actions: {},

  getters: {
    uriV2: state => `http://${state.host}:${state.port}/api/v2`,
    baseUri: state => `http://${state.host}:${state.port}`,
    ready: state => state.available
  }
});

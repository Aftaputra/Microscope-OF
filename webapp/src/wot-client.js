import axios from "axios";

export const wotStoreModule = {
  namespaced: true,
  state: () => ({
    thingDescriptions: {},
    servient: null,
    helpers: null
  }),
  mutations: {
    addThingDescription(state, { thingUri, thingDescription }) {
      state.thingDescriptions[thingUri] = thingDescription;
    },
    removeThingDescription(state, thingUri) {
      delete state.thingDescriptions[thingUri];
    },
    removeAllThingDescriptions(state) {
      state.thingDescriptions = {};
    }
  },
  actions: {
    async start() {
      // Set up thing client - not currently used.
    },
    async fetchThingDescription({ commit }, uri) {
      // Fetch the thing description from the given URI and consume it
      // NB this should only be called once, or we'll duplicate effort.
      // Deduplication should be done elsewhere.
      let response = await axios.get(uri);
      let td = response.data;
      commit("addThingDescription", { thingUri: uri, thingDescription: td });
    }
  },
  getters: {}
};

export default wotStoreModule;

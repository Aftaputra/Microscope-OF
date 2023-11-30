import axios from "axios";

export const wotStoreModule = {
  namespaced: true,
  state: () => ({
    thingDescriptions: {},
    servient: null,
    helpers: null
  }),
  mutations: {
    addThingDescription(state, { thingName, thingDescription }) {
      state.thingDescriptions[thingName] = thingDescription;
    },
    removeThingDescription(state, thingName) {
      delete state.thingDescriptions[thingName];
    },
    removeAllThingDescriptions(state) {
      state.thingDescriptions = {};
    }
  },
  actions: {
    async start() {
      // Set up thing client - not currently used.
    },
    async fetchThingDescription({ commit }, { uri, name = null }) {
      // Fetch the thing description from the given URI and consume it
      // NB this should only be called once, or we'll duplicate effort.
      // Deduplication should be done elsewhere.
      let response = await axios.get(uri);
      let td = response.data;
      let thing_name =
        name |
        uri
          .replace(/\/$/, "")
          .split("/")
          .pop();
      commit("addThingDescription", {
        thingName: thing_name,
        thingDescription: td
      });
    },
    async fetchThingDescriptions({ commit }, uri) {
      // Fetch thing descriptions from the given URI
      let response = await axios.get(uri);
      if (response.status != 200) throw "Could not retrieve thing descriptions";
      for (const k in response.data) {
        let thing_name = k.replace(/\/$/, "").replace(/^\//, "");
        commit("addThingDescription", {
          thingName: thing_name,
          thingDescription: response.data[k]
        });
      }
    }
  },
  getters: {
    thingDescription: state => thingName => {
      return state.thingDescriptions[thingName];
    },
    thingAvailable: state => thingName => {
      console.log("thingAvailable", thingName, state.thingDescriptions)
      return thingName in state.thingDescriptions;
    },
    thingFormUrl: state => (thing, affordanceType, affordance, op) => {
      // Find the URL for a particular operation
      let td = state.thingDescriptions[thing];
      if (!td) return null;
      let affordances = td[affordanceType];
      return findForm(affordances[affordance], op);
    },
    thingPropertyUrl: (_state, getters) => (thing, property, op) => {
      // Find the URL for a particular property
      return getters.thingFormUrl(thing, "properties", property, op);
    },
    thingActionUrl: (_state, getters) => (thing, action, op) => {
      // Find the URL for a particular action
      return getters.thingFormUrl(thing, "actions", action, op);
    }
  }
};

export function findForm(affordance, op) {
  // Find the form in the affordance that matches the given operation type
  let forms = affordance.forms;
  let matchingForm = forms.find(f => f.op == op || f.op.includes(op));
  return matchingForm.href;
}

export default wotStoreModule;

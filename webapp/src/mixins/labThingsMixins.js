/**
 * @fileoverview
 * Global mixin providing access to the LabThings (WoT) API.
 *
 * This mixin is registered globally in `main.js` using. Do not
 * manually import it in components.
 */

import axios from "axios";

export default {
  data() {
    return {
      pollTimers: {},
    };
  },

  methods: {
    thingDescription(thing) {
      return this.$store.getters["wot/thingDescription"](thing);
    },
    thingList() {
      return this.$store.getters["wot/thingList"];
    },
    thingAvailable(thing) {
      return this.$store.getters["wot/thingAvailable"](thing);
    },
    thingPropertyUrl(thing, property, allowUndefined = false) {
      return this.$store.getters["wot/thingPropertyUrl"](
        thing,
        property,
        "readproperty",
        allowUndefined,
      );
    },
    thingActionAvailable(thing, action) {
      return this.$store.getters["wot/thingAffordanceAvailable"](thing, "actions", action);
    },
    thingPropertyAvailable(thing, property) {
      return this.$store.getters["wot/thingAffordanceAvailable"](thing, "properties", property);
    },
    async readThingProperty(thing, property, silenceErrors = false) {
      let url = this.$store.getters["wot/thingPropertyUrl"](thing, property, "readproperty", false);
      try {
        let response = await axios.get(url);
        return response.data;
      } catch (error) {
        if (!silenceErrors) this.modalError(error);
        return undefined;
      }
    },
    async writeThingProperty(thing, property, value) {
      let url = this.$store.getters["wot/thingPropertyUrl"](
        thing,
        property,
        "writeproperty",
        false,
      );
      // `false` and 0 fail because axios turns it to ""
      // Other values should not be stringified or pydantic
      // can't parse them.
      if (value === false || value === true || value === 0) {
        value = JSON.stringify(value);
      }
      await axios.put(url, value);
    },
    async invokeAction(thing, action, data, handleErrors = true) {
      let url = this.thingActionUrl(thing, action);
      try {
        let response = await axios.post(url, data);
        return response;
      } catch (error) {
        if (handleErrors) {
          this.modalError(error);
          return undefined;
        } else {
          throw error;
        }
      }
    },
    async pollUntilComplete(
      taskUrl,
      ongoingMethod,
      finalMethod,
      interval = 500,
      modalErrors = true,
    ) {
      let response;
      let finalMethodCalled = false;
      try {
        response = await axios.get(taskUrl, { baseURL: this.$store.getters.baseUri });
        const result = response.data.status;

        if (result === "running" || result === "pending") {
          ongoingMethod?.(response);
          this.pollTimers[taskUrl] = setTimeout(() => {
            this.pollUntilComplete(taskUrl, ongoingMethod, finalMethod, interval);
          }, interval);
        } else {
          clearTimeout(this.pollTimers[taskUrl]);
          delete this.pollTimers[taskUrl];
          finalMethodCalled = true;
          finalMethod?.(response);
        }
      } catch (error) {
        this.$emit("error", error);
        if (modalErrors) {
          this.modalError(error);
        }
        clearTimeout(this.pollTimers[taskUrl]);
        delete this.pollTimers[taskUrl];
        if (!finalMethodCalled) {
          finalMethod?.(response);
        }
      }
    },
    terminateAction(taskUrl) {
      axios.delete(taskUrl, { baseURL: this.$store.getters.baseUri });
    },
    async findOngoingActions(thing, action) {
      let url = this.thingActionUrl(thing, action);
      try {
        return await axios.get(url);
      } catch (error) {
        console.warn("checkExistingTasks: request failed", error);
        return null;
      }
    },
    /**
     * Find and ongoing Action and return its task response.
     *
     * Returns null if there is no ongoing action
     */
    async getOngingAction(thing, action) {
      let response = await this.findOngoingActions(thing, action);
      // Exit if response is null, due to an error.
      if (response == null) return null;
      // Check for a task that is ongoing.
      // We can't handle multiple tasks ongoing, so this picks the first.
      // ?? Is the "Nullish Coalescing-Operator" to turn undefined into null.
      return response.data.find((t) => ["pending", "running"].includes(t.status)) ?? null;
    },
    thingActionUrl(thing, action, allowUndefined = false) {
      let url = this.$store.getters["wot/thingActionUrl"](
        thing,
        action,
        "invokeaction",
        allowUndefined,
      );
      return url;
    },
    async getThingEndpoint(thing, endpoint) {
      let url = `${this.$store.getters.baseUri}/${thing}/${endpoint}`;
      try {
        const response = await axios.get(url);
        return response.data;
      } catch {
        return undefined;
      }
    },
  },
};

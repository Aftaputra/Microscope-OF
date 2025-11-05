import Vue from "vue";
import App from "./App.vue";
import store from "./store";
import axios from "axios";
import UIkit from "uikit";

import VueObserveVisibility from "vue-observe-visibility";

// Import MD icons
import "material-symbols/outlined.css";

// UIKit overrides
UIkit.mixin(
  {
    data: {
      animation: false,
    },
  },
  "accordion",
);

// Use visibility observer
Vue.use(VueObserveVisibility);

Vue.config.productionTip = false;

Vue.mixin({
  methods: {
    thingDescription(thing) {
      return this.$store.getters["wot/thingDescription"](thing);
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
      // `false` fails because axios somehow eats it!
      // Other values should not be stringified or pydantic
      // can't parse them.
      if ((value === false) | (value === true)) {
        value = JSON.stringify(value);
      }
      await axios.put(url, value);
    },
    async invokeAction(thing, action, data) {
      let url = this.$store.getters["wot/thingActionUrl"](thing, action, "invokeaction", false);
      try {
        let response = await axios.post(url, data);
        return response;
      } catch (error) {
        this.modalError(error);
        return undefined;
      }
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
    modalConfirm: function (modalText) {
      var context = this;

      // Stop GPU preview to show modal
      context.$root.$emit("globalTogglePreview", false);

      // force OK to be capitalised
      UIkit.modal.i18n = { ok: "OK", cancel: "Cancel" };

      var showModal = function (resolve, reject) {
        UIkit.modal
          .confirm(modalText, { stack: true })
          .then(
            function () {
              resolve();
            },
            function () {
              reject();
            },
          )
          .finally(function () {
            // Re-enable the GPU preview, if it was active before the modal
            if (context.$store.state.autoGpuPreview) {
              context.$root.$emit("globalTogglePreview", true);
            }
            context.$root.$emit("modalClosed");
          });
      };
      return new Promise(showModal);
    },

    modalNotify: function (message, status = "success") {
      UIkit.notification({
        message: message,
        status: status,
      });
    },

    modalDialog: function (title, message) {
      UIkit.modal.dialog(
        `
        <button class="uk-modal-close-default" type="button" uk-close></button>
        <div class="uk-modal-header">
          <h2 class="uk-modal-title">${title}</h2>
        </div>
        <div class="uk-modal-body">
          <p>${message}</p>
        </div>
      `,
        { stack: true },
      );
    },

    modalError: function (error) {
      var errormsg = this.getErrorMessage(error);
      this.$store.commit("setErrorMessage", errormsg);
      UIkit.notification({
        message: `${errormsg}`,
        status: "danger",
      });
    },

    getErrorMessage: function (error) {
      // Format the error.
      let data = this.getErrorData(error);
      // Get error data may get an object. Handle edge cases and if not try to use
      // JSON to get the best string. This stops "objectObject" showing as an error.
      if (data === null) return "null";
      if (data === undefined) return "undefined";
      if (typeof data === "string") return data;
      try {
        return JSON.stringify(data, null, 2);
      } catch (err) {
        return String(data);
      }
    },
    getErrorData: function (error) {
      // If a response was obtained, extract the most specific message
      if (error.response) {
        // If the response is a nicely formatted JSON response from the server
        if (error.response.data.message) {
          return error.response.data.message;
        }
        if (error.response.data.detail) {
          try {
            return error.response.data.detail[0].msg;
          } catch (err) {
            return error.response.data.detail;
          }
        }
        // If the response is just some generic error response
        if (error.response.data) {
          return error.response.data;
        }
        return error.response;
      }
      // If we have an error object with a message, use that
      if (error.message) return error.message;
      // At this point just formatting the whole error object is the best we can do.
      return error;
    },

    showModalElement: function (element) {
      UIkit.modal(element).show();
    },

    hideModalElement: function (element) {
      UIkit.modal(element).hide();
    },

    toggleModalElement: function (element) {
      UIkit.modal(element).toggle();
    },
  },
});

new Vue({
  store,
  render: (h) => h(App),
}).$mount("#app");

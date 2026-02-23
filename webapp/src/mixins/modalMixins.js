/**
 * @fileoverview
 * Global mixin providing modal functionality.
 *
 * This mixin is registered globally in `main.js` using. Do not
 * manually import it in components.
 */

import UIkit from "uikit";
import { eventBus } from "@/eventBus";

export default {
  methods: {
    modalConfirm: function (modalText) {
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
            eventBus.emit("modalClosed");
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
      } catch {
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
          } catch {
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
};

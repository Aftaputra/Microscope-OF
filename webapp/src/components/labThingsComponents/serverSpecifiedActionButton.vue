<template>
  <action-button
    :thing="actionData.thing"
    :action="actionData.action"
    :poll-interval="actionData.poll_interval"
    :submit-label="actionData.submit_label"
    :can-terminate="actionData.can_terminate"
    :requires-confirmation="actionData.requires_confirmation"
    :confirmation-message="actionData.confirmation_message"
    :button-primary="actionData.button_primary"
    :modal-progress="actionData.modal_progress"
    @response="actionResponse"
    @error="modalError"
    @finished="actionFinished"
  />
</template>

<script>
import ActionButton from "./actionButton.vue";

// Export main app
export default {
  name: "ServerSpecifiedActionButton",

  components: {
    ActionButton,
  },

  props: {
    actionData: {
      type: Object,
      required: true,
    },
  },

  methods: {
    /**
     * Runs when the ActionButton's action completes successfully.
     *
     * It is used to send success notifications. It also forwards the response to the
     * parent.
     */
    actionResponse: function (response) {
      if (this.actionData.notify_on_success) {
        this.modalNotify(this.actionData.success_message);
        this.$emit("response", response);
      }
    },
    /**
     * Runs when the ActionButton's action finishes in any way (error, cancel,
     * completion).
     *
     * This forwards the event to the parent
     */
    actionFinished: function () {
      this.$emit("finished");
    },
  },
};
</script>

<style lang="less"></style>

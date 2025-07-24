<template>
  <div class="uk-padding-small">
    <div>
      <ul uk-accordion="multiple: true">
        <li>
          <a class="uk-accordion-title" href="#">Settings</a>
          <div class="uk-accordion-content">
            <p> TODO!</p>
          </div>
        </li>
      </ul>
      <div class="uk-margin">
        <action-button
          thing="camera"
          action="set_background"
          submit-label="Set Background"
          :can-terminate="false"
          :poll-interval="0.1"
          @response="alertBackgroundSet"
        />
      </div>
      <div class="uk-margin">
        <!--Once status is read this should be disabled id not ready..-->
        <action-button
          thing="camera"
          action="image_is_sample"
          submit-label="Check Current Image"
          :can-terminate="false"
          :poll-interval="0.1"
          @response="alertImageLabel"
          @error="backgroundDetectError"
        />
      </div>
    </div>
  </div>
</template>

<script>
import ActionButton from "../../labThingsComponents/actionButton.vue";

export default {
  components: {
    ActionButton
  },

  methods: {
    alertBackgroundSet() {
      this.modalNotify(`Background image has been updated`);
    },
    alertImageLabel(r) {
      let label = r.output[0] ? "sample" : "background";
      this.modalNotify(`Current image is ${label} (${r.output[1]})`);
    },
    backgroundDetectError() {
      this.modalError(
        "Background detection failed, most likely you need to set a background image." +
          " There may be more information in the log."
      );
    }
  }
};
</script>

<template>
  <div id="paneControl" class="uk-padding-small">
    <positionControl />

    <p>Autofocus</p>

    <div class="uk-grid-small uk-child-width-expand" uk-grid>
      <div v-show="!isAutofocusing || isAutofocusing == 1">
        <action-button
          thing="autofocus"
          action="fast_autofocus"
          :submit-data="{ dz: 2000 }"
          :submit-label="'Autofocus'"
          :button-primary="true"
          :submit-on-event="'globalFastAutofocusEvent'"
          @taskStarted="isAutofocusing = 1"
          @finished="
            updatePosition();
            isAutofocusing = 0;
          "
          @error="modalError"
        />
      </div>
    </div>

    <p>Image Capture</p>

    <div class="uk-margin">
      <action-button
        thing="camera"
        action="capture_jpeg"
        :submit-data="{ stream_name: 'main' }"
        :submit-label="'Low Resolution'"
        :submit-on-event="'globalCaptureEvent'"
        @response="handleCaptureResponse"
        @error="modalError"
      />
    </div>

    <div class="uk-margin">
      <action-button
        thing="camera"
        action="capture_jpeg"
        :submit-data="{ stream_name: 'full' }"
        submit-label="Full Resolution"
        :submit-on-event="'globalCaptureEvent'"
        @response="handleCaptureResponse"
        @error="modalError"
      />
    </div>
  </div>
</template>

<script>
import axios from "axios";
import ActionButton from "../../labThingsComponents/actionButton.vue";
import positionControl from "./positionControl.vue";

export default {
  name: "PaneControl",

  components: {
    ActionButton,
    positionControl,
  },

  data: function () {
    return {
      isAutofocusing: 0,
    };
  },

  methods: {
    handleCaptureResponse: async function (response) {
      // Retrieve the captured image and save it
      let imageUri = response.output.href;
      if (!imageUri) {
        this.modalError("No image URI returned from capture task.");
        console.log(`Capture resulted in response ${response}`);
        return;
      }
      // To save the returned data, we make a virtual link and click it
      let imageResponse = await axios.get(imageUri, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([imageResponse.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `OFM_${new Date().toISOString()}.jpeg`);
      document.body.appendChild(link);
      link.click();
    },
  },
};
</script>

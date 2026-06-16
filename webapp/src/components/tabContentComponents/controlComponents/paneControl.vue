<template>
  <div id="paneControl" class="uk-padding-small">
    <positionControl v-if="stageAvailable" />
    <autofocusControl v-if="autofocusAvailable" />
    <p>Image Capture</p>

    <div class="uk-margin">
      <action-button
        thing="camera"
        action="capture"
        :submit-data="{ capture_mode: 'standard' }"
        submit-label="Capture"
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
import autofocusControl from "./autofocusControl.vue";
import { eventBus } from "../../../eventBus.js";

export default {
  name: "PaneControl",

  components: {
    ActionButton,
    positionControl,
    autofocusControl,
  },

  computed: {
    stageAvailable() {
      return this.thingAvailable("stage");
    },
    autofocusAvailable() {
      return this.thingAvailable("autofocus");
    },
  },

  methods: {
    handleCaptureResponse: async function (response) {
      // Retrieve the captured image and save it
      let imageUri = response.output.href;
      if (!imageUri) {
        this.modalError("No image URI returned from capture task.");
        return;
      }
      // Emit flash capture stream animation
      eventBus.emit("globalFlashStream");

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

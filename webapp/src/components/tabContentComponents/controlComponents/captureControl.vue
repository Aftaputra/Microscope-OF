<template>
  <div id="captureControl">
    <p><b>Image Capture</b></p>

    <toggle-switch
      v-model="saveToGallery"
      label-text="Save to Gallery?"
      on-label="Saving"
      off-label="Downloading"
    />

    <div class="uk-margin">
      <action-button
        thing="camera"
        action="capture"
        :submit-data="submitData"
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
import toggleSwitch from "@/components/genericComponents/toggleSwitch.vue";
import ActionButton from "@/components/labThingsComponents/actionButton.vue";

export default {
  name: "CaptureControl",

  components: {
    toggleSwitch,
    ActionButton,
  },

  data: function () {
    return {
      saveToGallery: true,
    };
  },

  computed: {
    submitData() {
      return {
        capture_mode: "standard",
        retain_image: this.saveToGallery,
      };
    },
  },

  methods: {
    handleCaptureResponse: async function (response) {
      // Retrieve the captured image and save it
      if (this.saveToGallery) return;
      let imageUri = response.output.href;
      if (!imageUri) {
        this.modalError("No image URI returned from capture task.");
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

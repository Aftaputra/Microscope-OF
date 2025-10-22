<template>
  <stepTemplateWithStream>
    <p>
      <b>
        <p>Once you're ready, click auto-calibrate.</p>

          <cameraCalibrationSettings
            :show-extra-settings="false"
            :camera-uri="cameraUri"
          ></cameraCalibrationSettings>
      </b>
    </p>
  </stepTemplateWithStream>
</template>

<script>
import stepTemplateWithStream from "../stepTemplateWithStream.vue"
import cameraCalibrationSettings from "../../../tabContentComponents/settingsComponents/cameraSettingsComponents/cameraCalibrationSettings.vue";

export default {
  name: "cameraMainCalibrationStep",

  components: {
    stepTemplateWithStream,
    cameraCalibrationSettings
  },

  computed: {
    cameraUri: function() {
      return `${this.$store.getters.baseUri}/camera/`;
    }
  }
}
</script>

<template>
  <stepTemplateWithStream>
    <p>
      <b>Once your field of view is empty and well illuminated, click Full Auto-Calibrate.</b>
    </p>

    <template #below-stream>
      <div class="action-button-container">
        <cameraCalibrationSettings
          :show-extra-settings="false"
          :camera-uri="cameraUri"
        />
      </div>
    </template>
  </stepTemplateWithStream>
</template>

<script>
import stepTemplateWithStream from "../stepTemplateWithStream.vue";
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
};
</script>

<style scoped>
.action-button-container {
  padding: 4px;
}
</style>

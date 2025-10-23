<template>
  <stepTemplateWithStream>
    <p>
      <b>Once you're ready, click Auto-Calibrate Using Camera.</b>
    </p>
    <template #below-stream>
      <div class="action-button-container">
        <CSMCalibrationSettings :show-extra-settings="false" />
      </div>
    </template>
  </stepTemplateWithStream>
</template>

<script>
import stepTemplateWithStream from "../stepTemplateWithStream.vue";
import CSMCalibrationSettings from "../../../tabContentComponents/settingsComponents/CSMSettingsComponents/CSMCalibrationSettings.vue";

export default {
  name: "cameraMainCalibrationStep",

  components: {
    stepTemplateWithStream,
    CSMCalibrationSettings
  }
};
</script>

<style scoped>
.action-button-container {
  padding: 4px;
}
</style>

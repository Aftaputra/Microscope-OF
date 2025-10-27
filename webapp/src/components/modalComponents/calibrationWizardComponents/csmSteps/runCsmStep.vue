<template>
  <stepTemplateWithStream>
    <p>
      <b>If the sample is in focus, click Auto-Calibrate Using Camera.</b>
    </p>
    <p>If it is not in focus, click back and re-focus.</p>
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

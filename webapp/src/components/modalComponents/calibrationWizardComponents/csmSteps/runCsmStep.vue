<template>
  <stepTemplateWithStream>
    <p>
      <b>If the sample is in focus, click Auto-Calibrate Using Camera.</b>
    </p>
    <p>If it is not in focus, click back and re-focus.</p>
    <template #below-stream>
      <div class="action-button-container">
        <CSMCalibrationSettings
          :show-extra-settings="false"
          @recalibrateResponse="checkCalibrationState"
        />
      </div>
    </template>
  </stepTemplateWithStream>
</template>

<script>
import stepTemplateWithStream from "../stepTemplateWithStream.vue";
import CSMCalibrationSettings from "../../../tabContentComponents/settingsComponents/CSMSettingsComponents/CSMCalibrationSettings.vue";
// vue3 migration
import { markRaw } from "vue";

export default {
  name: "CameraMainCalibrationStep",

  components: {
    stepTemplateWithStream: markRaw(stepTemplateWithStream),
    CSMCalibrationSettings: markRaw(CSMCalibrationSettings),
  },

  mounted() {
    this.checkCalibrationState();
  },

  methods: {
    async checkCalibrationState() {
      const needsCal = await this.readThingProperty("camera_stage_mapping", "calibration_required");
      this.$emit("awaiting-user", needsCal);
    },
  },
};
</script>

<style scoped>
.action-button-container {
  padding: 4px;
}
</style>

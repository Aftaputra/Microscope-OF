<template>
  <stepTemplateWithStream>
    <p>
      <b
        >Once your field of view appears empty, and the illumination looks centred, click Full
        Auto-Calibrate.</b
      >
    </p>

    <template #below-stream>
      <div class="action-button-container">
        <cameraCalibrationSettings
          :show-extra-settings="false"
          :camera-uri="cameraUri"
          @action-finished="checkCalibrationState"
        />
      </div>
    </template>
  </stepTemplateWithStream>
</template>

<script>
import stepTemplateWithStream from "../stepTemplateWithStream.vue";
import cameraCalibrationSettings from "../../../tabContentComponents/settingsComponents/cameraSettingsComponents/cameraCalibrationSettings.vue";

export default {
  name: "CameraMainCalibrationStep",

  components: {
    stepTemplateWithStream,
    cameraCalibrationSettings,
  },

  emits: ["awaiting-user"],

  computed: {
    cameraUri: function () {
      return `${this.$store.getters.baseUri}/camera/`;
    },
  },

  mounted() {
    this.checkCalibrationState();
  },

  methods: {
    async checkCalibrationState() {
      const needsCal = await this.readThingProperty("camera", "calibration_required");
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

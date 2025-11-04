<template>
  <div id="cameraSettings">
    <div class="uk-grid uk-grid-divider uk-child-width-expand" uk-grid>
      <div class="uk-width-large">
        <h3>Automatic calibration</h3>
        <cameraCalibrationSettings :camera-uri="cameraUri" />
        <h3>Manual camera settings</h3>
        <div class="uk-margin-small-bottom">
          <server-specified-property-control
            v-for="(setting, index) in manualCameraSettings"
            :key="'cam_setting' + index"
            :property-data="setting"
          />
        </div>
      </div>

      <div id="mini-stream">
        <miniStreamDisplay />
      </div>
    </div>
  </div>
</template>

<script>
import cameraCalibrationSettings from "./cameraSettingsComponents/cameraCalibrationSettings.vue";
import miniStreamDisplay from "../../genericComponents/miniStreamDisplay.vue";
import ServerSpecifiedPropertyControl from "../../labThingsComponents/serverSpecifiedPropertyControl.vue";

// Export main app
export default {
  name: "CameraSettings",

  components: {
    cameraCalibrationSettings,
    miniStreamDisplay,
    ServerSpecifiedPropertyControl,
  },

  data() {
    return {
      manualCameraSettings: [],
    };
  },

  computed: {
    cameraUri: function () {
      return `${this.$store.getters.baseUri}/camera/`;
    },
  },

  async created() {
    this.manualCameraSettings = await this.readThingProperty("camera", "manual_camera_settings");
  },
};
</script>

<style lang="less">
#mini-stream {
  min-width: 300px;
  max-width: 600px;
  text-align: center;
  margin-left: auto;
  margin-right: auto;
  margin-top: 50px;
}
</style>

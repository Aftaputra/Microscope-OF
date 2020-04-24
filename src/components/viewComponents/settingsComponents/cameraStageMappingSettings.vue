<template>
  <div id="cameraStageMappingSettings">
    <h3>Camera/stage mapping</h3>
    <p>
      Camera/stage mapping allows the stage to move relative to the camera view.
      This enables functions like click-to-move, and more precise tile scans.
    </p>
    <form @submit.prevent="applyConfigRequest">
      <!--Show auto calibrate if default plugin is enabled-->
      <div v-if="'calibrate_xy' in recalibrationLinks" class="uk-margin-small">
        <taskSubmitter
          :can-terminate="false"
          :requires-confirmation="true"
          :confirmation-message="
            'Start recalibration of the stage to the camera? This may take a while, and the microscope will be locked during this time.'
          "
          :submit-url="recalibrationLinks.calibrate_xy.href"
          :submit-label="'Auto-Calibrate using camera'"
          @response="onRecalibrateResponse"
          @error="onRecalibrateError"
        >
        </taskSubmitter>
      </div>
    </form>
  </div>
</template>

<script>
import axios from "axios";
import taskSubmitter from "../../genericComponents/taskSubmitter";

// Export main app
export default {
  name: "CameraStageMappingSettings",

  components: {
    taskSubmitter
  },

  data: function() {
    return {
      settings: null,
      recalibrationLinks: {},
      isCalibrating: false
    };
  },

  computed: {
    settingsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/instrument/settings`;
    },
    pluginsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/extensions`;
    }
  },

  mounted() {
    this.updateSettings();
    this.updateRecalibrationLinks();
  },

  methods: {
    updateSettings: function() {
      axios
        .get(this.settingsUri)
        .then(response => {
          this.settings =
            response.data.extensions["org.openflexure.camera_stage_mapping"];
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
          this.settings = {};
        });
    },

    updateRecalibrationLinks: function() {
      axios
        .get(this.pluginsUri) // Get a list of plugins
        .then(response => {
          var plugins = response.data;
          var foundExtension = plugins.find(
            e => e.title === "org.openflexure.camera_stage_mapping"
          );
          // if camera-stage mapping extension is enabled
          if (foundExtension) {
            // Get plugin action link
            this.recalibrationLinks = foundExtension.links;
          } else {
            this.recalibrationLinks = {};
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    onRecalibrateResponse: function() {
      this.modalNotify("Finished stage-to-camera calibration.");
      // Update local settings
      this.updateSettings();
    },

    onRecalibrateError: function(error) {
      this.modalError(error); // Let mixin handle error
    }
  }
};
</script>

<style lang="less">
.center-spinner {
  margin-left: auto;
  margin-right: auto;
}
</style>

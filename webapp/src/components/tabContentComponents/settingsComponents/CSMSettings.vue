<template>
  <div
    id="CSMSettings"
    class="uk-grid uk-grid-divider uk-child-width-expand"
    uk-grid
  >
    <div class="uk-width-large">
      <h3>Camera/stage mapping</h3>
      <p>
        Camera/stage mapping allows the stage to move relative to the camera
        view. This enables functions like click-to-move, and more precise tile
        scans.
      </p>
      <CSMCalibrationSettings />
    </div>
    <div id="mini-stream">
      <miniStreamDisplay />
    </div>
  </div>
</template>

<script>
import axios from "axios";
import CSMCalibrationSettings from "./CSMSettingsComponents/CSMCalibrationSettings.vue";
import miniStreamDisplay from "../../genericComponents/miniStreamDisplay.vue";

// Export main app
export default {
  name: "CSMSettings",

  components: {
    CSMCalibrationSettings,
    miniStreamDisplay
  },

  props: {
    showExtraSettings: {
      type: Boolean,
      required: false,
      default: true
    }
  },

  data: function() {
    return {
      thingDescription: undefined,
      recalibrationLinks: {},
      isCalibrating: false,
      dataAvailable: false
    };
  },

  computed: {
  },

  mounted() {
    this.updateThingDescription();
  },

  methods: {
    updateCalibrationDataAvailability: function() {
      if ("get_calibration" in this.recalibrationLinks) {
        axios
          .get(this.recalibrationLinks.get_calibration.href)
          .then(response => {
            if (Object.keys(response.data).length === 0) {
              this.dataAvailable = false;
            } else {
              this.dataAvailable = true;
            }
          })
          .catch(error => {
            this.modalError(error); // Let mixin handle error
          });
      }
    },

    getCalibrationData: function() {
      axios
        .get(this.recalibrationLinks.get_calibration.href)
        .then(response => {
          if (response.data != {}) {
            const data = JSON.stringify(response.data);
            const url = window.URL.createObjectURL(new Blob([data]));
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute("download", "csm_calibration.json");
            document.body.appendChild(link);
            link.click();
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    updateThingDescription: function() {
      this.thingDescription = 
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
            // Update whether calibration data is available
            this.updateCalibrationDataAvailability();
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
#mini-stream {
  min-width: 300px;
  max-width: 600px;
  text-align: center;
  margin-left: auto;
  margin-right: auto;
  margin-top: 50px;
}
</style>

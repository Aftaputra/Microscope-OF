<template>
  <div id="modal-example" ref="calibrationModalEl" uk-modal>
    <div v-if="ready" class="uk-modal-dialog uk-modal-body">
      <h2 class="uk-modal-title">Microscope Calibration</h2>
      <div v-show="stepValue == 0">
        <p>
          <b
            >Some important microscope calibration data is currently missing.</b
          >
        </p>
        <p>
          Your microscope will still function, however some functionality will
          be limited, and image quality will likely suffer.
        </p>
        <p>
          <b>Click Next to begin microscope calibration.</b>
        </p>
      </div>

      <div v-show="stepValue == 1">
        <h3>Lens-shading</h3>
        <div v-if="isLSTCalibrated">
          <p>
            <b
              >Your lens-shading table has already been calibrated. Click Next
              to move on.</b
            >
          </p>
        </div>
        <div v-else>
          <p>
            <b
              >Follow the important steps below before starting lens-shading
              calibration!</b
            >
          </p>
          <ul class="uk-list uk-list-bullet">
            <li>Remove any samples from your microscope</li>
            <li>Ensure your illumination is on and properly fixed in place</li>
          </ul>

          <miniStreamDisplay
            v-if="stepValue == 1"
            class="mini-preview"
          ></miniStreamDisplay>

          <p>Once you're ready, click auto-calibrate.</p>

          <cameraCalibrationSettings
            :show-extra-settings="false"
          ></cameraCalibrationSettings>
        </div>
      </div>

      <div v-show="stepValue == 2">
        <h3>Camera-stage mapping</h3>
        <div v-if="isCSMCalibrated">
          <p>
            <b
              >Your camera-stage mapping has already been calibrated. Click Next
              to move on.</b
            >
          </p>
        </div>
        <div v-else>
          <p>
            <b
              >Follow the important steps below before starting camera-stage
              mapping calibration!</b
            >
          </p>
          <ul class="uk-list uk-list-bullet">
            <li>Insert a clearly visible sample to the microscope</li>
            <li>
              Ensure the sample is reasonably well centered on the microscope
              camera
            </li>
          </ul>

          <miniStreamDisplay
            v-if="stepValue == 2"
            class="mini-preview"
          ></miniStreamDisplay>

          <p>Once you're ready, click auto-calibrate.</p>

          <cameraStageMappingSettings
            :show-extra-settings="false"
          ></cameraStageMappingSettings>
        </div>
      </div>

      <div v-show="stepValue == 3">
        <p>
          <b>Calibration complete</b>
        </p>
        <p>
          Click Finish to return to your microscope, or Restart to re-run the
          calibration routine
        </p>
      </div>

      <p class="uk-text-right">
        <button
          v-show="stepValue == 0"
          class="uk-button uk-button-default uk-modal-close"
          type="button"
        >
          Cancel
        </button>
        <button
          v-show="stepValue == 3"
          class="uk-button uk-button-default"
          type="button"
          @click="stepValue = 0"
        >
          Restart
        </button>
        <button
          v-show="stepValue < 3"
          class="uk-button uk-button-primary uk-margin-left"
          type="button"
          @click="increment()"
        >
          Next
        </button>
        <button
          v-show="stepValue == 3"
          class="uk-button uk-button-primary uk-margin-left"
          type="button"
          @click="hide()"
        >
          Finish
        </button>
      </p>
    </div>
  </div>
</template>

<script>
import axios from "axios";

import cameraCalibrationSettings from "../viewComponents/settingsComponents/cameraCalibrationSettings.vue";
import cameraStageMappingSettings from "../viewComponents/settingsComponents/cameraStageMappingSettings.vue";
import miniStreamDisplay from "../viewComponents/miniStreamDisplay.vue";

export default {
  name: "CalibrationModal",

  components: {
    cameraCalibrationSettings,
    cameraStageMappingSettings,
    miniStreamDisplay
  },

  props: {
    availablePlugins: {
      type: Array,
      required: true
    }
  },

  data: function() {
    return {
      ready: false,
      stepValue: 0,
      settings: {}
    };
  },

  computed: {
    settingsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/instrument/settings`;
    },
    availablePluginTitles: function() {
      return this.availablePlugins.map(a => a.title);
    },
    isCSMCalibrated: function() {
      if (this.settings.extensions["org.openflexure.camera_stage_mapping"]) {
        return true;
      } else {
        return false;
      }
    },
    isLSTCalibrated: function() {
      if (
        this.settings.camera.picamera &&
        this.settings.camera.picamera.lens_shading_table
      ) {
        return true;
      } else {
        return false;
      }
    },
    canCSMCalibrated: function() {
      return this.availablePluginTitles.includes(
        "org.openflexure.camera_stage_mapping"
      );
    },
    canLSTCalibrated: function() {
      return this.availablePluginTitles.includes(
        "org.openflexure.calibration.picamera"
      );
    },
    isUseful: function() {
      var CSMUseful = this.canCSMCalibrated && !this.isCSMCalibrated;
      var LSTUseful = this.canLSTCalibrated && !this.isLSTCalibrated;
      return CSMUseful || LSTUseful;
    }
  },

  methods: {
    show: function() {
      // Get current settings
      this.getSettings().then(() => {
        // Check if this calibration wizard can actually do anything useful
        console.log(this.isUseful);
        if (this.isUseful) {
          this.ready = true;
          this.stepValue = 0;
          // Show the modal
          var el = this.$refs["calibrationModalEl"];
          this.showModalElement(el); // Calls the mixin
        }
      });
    },

    hide: function() {
      // Show the modal
      var el = this.$refs["calibrationModalEl"];
      this.hideModalElement(el); // Calls the mixin
      this.ready = false;
    },

    getSettings: function() {
      return axios
        .get(this.settingsUri)
        .then(response => {
          this.settings = response.data;
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    decrement: function() {
      if (this.stepValue > 0) {
        this.stepValue = this.stepValue - 1;
      }
    },

    increment: function() {
      // Upper bound on section number
      if (this.stepValue < 3) {
        this.stepValue = this.stepValue + 1;
        return true;
      }
    }
  }
};
</script>

<style scoped>
.mini-preview {
  width: 75%;
  margin-left: auto;
  margin-right: auto;
  border: 1px solid #555;
}
</style>

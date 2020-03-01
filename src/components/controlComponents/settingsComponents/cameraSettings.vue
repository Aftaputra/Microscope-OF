<template>
  <div v-if="settings" id="cameraSettings">
    <form @submit.prevent="applyConfigRequest">
      <div v-if="settings.picamera">
        <!--PiCamera settings block-->
        <div v-if="settings.picamera.shutter_speed !== undefined">
          <label class="uk-form-label" for="form-stacked-text"
            >Exposure time</label
          >
          <div class="uk-form-controls">
            <input
              v-model="settings.picamera.shutter_speed"
              class="uk-input uk-form-small"
              type="number"
            />
          </div>
        </div>

        <div v-if="settings.picamera.analog_gain !== undefined">
          <label class="uk-form-label" for="form-stacked-text"
            >Analogue gain</label
          >
          <div class="uk-form-controls">
            <input
              v-model="settings.picamera.analog_gain"
              class="uk-input uk-form-small"
              type="number"
              step="0.000001"
            />
          </div>
        </div>

        <div v-if="settings.picamera.digital_gain !== undefined">
          <label class="uk-form-label" for="form-stacked-text"
            >Digital gain</label
          >
          <div class="uk-form-controls">
            <input
              v-model="settings.picamera.digital_gain"
              class="uk-input uk-form-small"
              type="number"
              step="0.000001"
            />
          </div>
        </div>
      </div>

      <button
        type="submit"
        class="uk-button uk-button-primary uk-form-small uk-float-right uk-margin-small uk-width-1-1"
      >
        Apply Settings
      </button>

      <!--Show auto calibrate if default plugin is enabled-->
      <div v-if="recalibrationUri">
        <taskSubmitter
          :can-terminate="false"
          :requires-confirmation="true"
          :confirmation-message="
            'Start recalibration? This may take a while, and the microscope will be locked during this time.'
          "
          :submit-url="recalibrationUri"
          :submit-label="'Auto-Calibrate'"
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
  name: "CameraSettings",

  components: {
    taskSubmitter
  },

  data: function() {
    return {
      settings: null,
      recalibrationUri: null,
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
    this.updateRecalibrationUri();
  },

  methods: {
    updateSettings: function() {
      axios
        .get(this.settingsUri)
        .then(response => {
          this.settings = response.data.camera;
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    updateRecalibrationUri: function() {
      axios
        .get(this.pluginsUri) // Get a list of plugins
        .then(response => {
          var plugins = response.data;
          var foundExtension = plugins.find(
            e => e.title === "org.openflexure.calibration.picamera"
          );
          // if AutocalibrationPlugin is enabled
          if (foundExtension) {
            // Get plugin action link
            this.recalibrationUri = foundExtension.links.recalibrate.href;
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    applyConfigRequest: function() {
      console.log("Applying config to the microscope");
      var payload = {
        camera: {
          picamera: {
            shutter_speed: this.settings.picamera.shutter_speed,
            analog_gain: this.settings.picamera.analog_gain,
            digital_gain: this.settings.picamera.digital_gain
          }
        }
      };

      // Send request
      axios
        .put(this.settingsUri, payload)
        .then(() => {
          return new Promise(r => setTimeout(r, 500));
        }) // why is there no built-in for this??!
        .then(() => {
          // Update local settings
          this.updateSettings();
          this.modalNotify("Camera settings applied.");
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    onRecalibrateResponse: function() {
      this.modalNotify("Finished recalibration.");
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

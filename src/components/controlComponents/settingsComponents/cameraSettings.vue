<template>
  <div v-if="camera_settings" id="cameraSettings">
    <form @submit.prevent="applyConfigRequest">
      <div v-if="camera_settings.picamera_settings.shutter_speed">
        <label class="uk-form-label" for="form-stacked-text"
          >Exposure time</label
        >
        <div class="uk-form-controls">
          <input
            v-model="camera_settings.picamera_settings.shutter_speed"
            class="uk-input uk-form-small"
            type="number"
          />
        </div>
      </div>

      <div v-if="camera_settings.picamera_settings.analog_gain">
        <label class="uk-form-label" for="form-stacked-text"
          >Analogue gain</label
        >
        <div class="uk-form-controls">
          <input
            v-model="camera_settings.picamera_settings.analog_gain"
            class="uk-input uk-form-small"
            type="number"
            step="0.000001"
          />
        </div>
      </div>

      <div v-if="camera_settings.picamera_settings.digital_gain">
        <label class="uk-form-label" for="form-stacked-text"
          >Digital gain</label
        >
        <div class="uk-form-controls">
          <input
            v-model="camera_settings.picamera_settings.digital_gain"
            class="uk-input uk-form-small"
            type="number"
            step="0.000001"
          />
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
          :submit-label="'Auto-Calibrate (Task)'"
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
      camera_settings: null,
      recalibrationUri: null,
      isCalibrating: false
    };
  },

  computed: {
    settingsUri: function() {
      return `http://${this.$store.state.host}:${
        this.$store.state.port
      }/api/v2/settings`;
    },
    pluginsUri: function() {
      return `http://${this.$store.state.host}:${
        this.$store.state.port
      }/api/v2/plugins`;
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
          this.camera_settings = response.data.camera_settings;
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
          // if AutocalibrationPlugin is enabled
          if ("AutocalibrationPlugin" in plugins) {
            // Get plugin action link
            var link =
              plugins.AutocalibrationPlugin.views.recalibrate.links.self;
            // Store plugin action URI
            this.recalibrationUri = `http://${this.$store.state.host}:${
              this.$store.state.port
            }${link}`;
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    applyConfigRequest: function() {
      console.log("Applying config to the microscope");
      var payload = {
        camera_settings: {
          picamera_settings: {
            shutter_speed: this.camera_settings.picamera_settings.shutter_speed,
            analog_gain: this.camera_settings.picamera_settings.analog_gain,
            digital_gain: this.camera_settings.picamera_settings.digital_gain
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
          return this.$store.dispatch("updateConfig");
        })
        .then(this.updateInputValues)
        .then(() => {
          console.log("Updated Config: ", payload);
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    onRecalibrateResponse: function() {
      this.modalNotify("Finished recalibration.");
      return new Promise(r => setTimeout(r, 500)); // wait 500ms before updating config, so it's fresh
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

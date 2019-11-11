<template>
  <div id="cameraSettings">
    <form @submit.prevent="applyConfigRequest">
      <div>
        <label class="uk-form-label" for="form-stacked-text"
          >Exposure time</label
        >
        <div class="uk-form-controls">
          <input
            :value="displayShutterSpeed"
            class="uk-input uk-form-small"
            type="number"
            @input="shutterSpeed = $event.target.value"
          />
        </div>
      </div>

      <div>
        <label class="uk-form-label" for="form-stacked-text"
          >Analogue gain</label
        >
        <div class="uk-form-controls">
          <input
            :value="displayAnalogGain"
            class="uk-input uk-form-small"
            type="number"
            step="0.1"
            @input="analogGain = $event.target.value"
          />
        </div>
      </div>

      <div>
        <label class="uk-form-label" for="form-stacked-text"
          >Digital gain</label
        >
        <div class="uk-form-controls">
          <input
            :value="displayDigitalGain"
            class="uk-input uk-form-small"
            type="number"
            step="0.1"
            @input="digitalGain = $event.target.value"
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
      <div
        v-if="
          this.$store.state.apiState.plugin.includes(
            'default_camera_calibration'
          )
        "
      >
        <taskSubmitter
          :can-terminate="false"
          :requires-confirmation="true"
          :confirmation-message="
            'Start recalibration? This may take a while, and the microscope will be locked during this time.'
          "
          :submit-u-r-l="recalibrateApiUri"
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
  name: "MicroscopeSettings",

  components: {
    taskSubmitter
  },

  data: function() {
    return {
      shutterSpeed: this.$store.state.apiConfig.camera_settings
        .picamera_settings.shutter_speed,
      analogGain: this.$store.state.apiConfig.camera_settings.picamera_settings
        .analog_gain,
      digitalGain: this.$store.state.apiConfig.camera_settings.picamera_settings
        .digital_gain,
      isCalibrating: false
    };
  },

  computed: {
    displayDigitalGain: function() {
      return Number(this.digitalGain).toFixed(2);
    },
    displayAnalogGain: function() {
      return Number(this.analogGain).toFixed(2);
    },
    displayShutterSpeed: function() {
      return this.shutterSpeed != "0" ? this.shutterSpeed : "auto";
    },
    recalibrateApiUri: function() {
      return (
        this.$store.getters.uri +
        "/plugin/default/camera_calibration/recalibrate"
      );
    },
    configApiUri: function() {
      return this.$store.getters.uri + "/config";
    }
  },

  methods: {
    updateInputValues: function() {
      this.shutterSpeed = this.$store.state.apiConfig.camera_settings.picamera_settings.shutter_speed;
      this.digitalGain = this.$store.state.apiConfig.camera_settings.picamera_settings.digital_gain;
      this.analogGain = this.$store.state.apiConfig.camera_settings.picamera_settings.analog_gain;
    },

    applyConfigRequest: function() {
      console.log("Applying config to the microscope");
      var payload = {
        camera_settings: {
          picamera_settings: {}
        }
      };

      //if (this.shutterSpeed != this.$store.state.apiConfig.picamera_settings.shutter_speed) {
      payload.camera_settings.picamera_settings.shutter_speed = this.shutterSpeed;
      payload.camera_settings.picamera_settings.analog_gain = this.analogGain;
      payload.camera_settings.picamera_settings.digital_gain = this.digitalGain;
      //};

      // Send request
      axios
        .post(this.configApiUri, payload)
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

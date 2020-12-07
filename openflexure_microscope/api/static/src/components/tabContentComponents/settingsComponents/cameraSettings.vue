<template>
  <div id="cameraSettings">
    <div class="uk-grid uk-grid-divider uk-child-width-expand" uk-grid>
      <div class="uk-width-large">
        <h3>Manual camera settings</h3>
        <form @submit.prevent="applySettingsRequest">
          <div class="uk-margin-small-bottom">
            <h4>Raspberry Pi Camera</h4>
            <!--PiCamera settings block-->
            <div v-if="picamera.shutter_speed !== undefined">
              <label class="uk-form-label" for="form-stacked-text"
                >Exposure time</label
              >
              <div class="uk-form-controls">
                <input
                  v-model="picamera.shutter_speed"
                  class="uk-input uk-form-small"
                  type="number"
                />
              </div>
            </div>

            <div v-if="picamera.analog_gain !== undefined">
              <label class="uk-form-label" for="form-stacked-text"
                >Analogue gain</label
              >
              <div class="uk-form-controls">
                <input
                  v-model="picamera.analog_gain"
                  class="uk-input uk-form-small"
                  type="number"
                  step="0.000001"
                />
              </div>
            </div>

            <div v-if="picamera.digital_gain !== undefined">
              <label class="uk-form-label" for="form-stacked-text"
                >Digital gain</label
              >
              <div class="uk-form-controls">
                <input
                  v-model="picamera.digital_gain"
                  class="uk-input uk-form-small"
                  type="number"
                  step="0.000001"
                />
              </div>
            </div>
          </div>

          <div class="uk-margin-small-bottom">
            <h4>Image quality</h4>

            <div class="uk-child-width-1-2" uk-grid>
              <div v-if="mjpeg_bitrate !== undefined">
                <label class="uk-form-label" for="form-stacked-text"
                  >Web stream bitrate</label
                >
                <select v-model="mjpeg_bitrate" class="uk-select uk-form-small">
                  <option
                    v-for="option in bitrateOptions"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.text }}
                  </option>
                </select>
              </div>

              <div v-if="jpeg_quality !== undefined">
                <label class="uk-form-label" for="form-stacked-text"
                  >JPEG capture quality (%)</label
                >
                <div class="uk-form-controls">
                  <input
                    v-model="jpeg_quality"
                    class="uk-input uk-form-small"
                    type="number"
                    step="1"
                  />
                </div>
              </div>
            </div>

            <span
              v-if="
                mjpeg_bitrate !== undefined &&
                  mjpeg_bitrate < 17000000 &&
                  mjpeg_bitrate != -1
              "
              class="uk-text-danger uk-margin-top-small"
              >This stream bitrate may impact fast autofocus performance</span
            >
          </div>

          <button
            type="submit"
            class="uk-button uk-button-primary uk-margin-small uk-width-1-1"
          >
            Apply Settings
          </button>
        </form>

        <h3>Automatic calibration</h3>
        <cameraCalibrationSettings></cameraCalibrationSettings>
      </div>

      <div id="mini-stream">
        <miniStreamDisplay />
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import cameraCalibrationSettings from "./cameraSettingsComponents/cameraCalibrationSettings.vue";
import miniStreamDisplay from "../../genericComponents/miniStreamDisplay.vue";

// Export main app
export default {
  name: "CameraSettings",

  components: {
    cameraCalibrationSettings,
    miniStreamDisplay
  },

  data: function() {
    return {
      picamera: {
        shutter_speed: undefined,
        analog_gain: undefined,
        digital_gain: undefined
      },
      mjpeg_bitrate: undefined,
      jpeg_quality: undefined,
      bitrateOptions: [
        { text: "Maximum", value: -1 },
        { text: "High", value: 25000000 },
        { text: "Normal", value: 17000000 },
        { text: "Low", value: 5000000 },
        { text: "Very low", value: 2500000 }
      ]
    };
  },

  computed: {
    settingsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/instrument/settings`;
    }
  },

  mounted() {
    this.updateSettings();
  },

  methods: {
    updateSettings: function() {
      axios
        .get(this.settingsUri)
        .then(response => {
          const cameraSettings = response.data.camera;
          // Get base camera settings
          this.mjpeg_bitrate = cameraSettings.mjpeg_bitrate;
          this.jpeg_quality = cameraSettings.jpeg_quality;
          // Get Pi Camera settings if they exist
          if (cameraSettings.picamera) {
            this.picamera.analog_gain = cameraSettings.picamera.analog_gain;
            this.picamera.digital_gain = cameraSettings.picamera.digital_gain;
            this.picamera.shutter_speed = cameraSettings.picamera.shutter_speed;
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    applySettingsRequest: function() {
      // We have to use parseInt/parseFloat because JS sometimes seems to
      // make the numbers be strings... TypeScript would solve this...
      var payload = {
        camera: {
          mjpeg_bitrate: parseInt(this.mjpeg_bitrate),
          jpeg_quality: parseInt(this.jpeg_quality),
          picamera: {
            shutter_speed: parseFloat(this.picamera.shutter_speed),
            analog_gain: parseFloat(this.picamera.analog_gain),
            digital_gain: parseFloat(this.picamera.digital_gain)
          }
        }
      };
      console.log(payload);
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
    }
  }
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

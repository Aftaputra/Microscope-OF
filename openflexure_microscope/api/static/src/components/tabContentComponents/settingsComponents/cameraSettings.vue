<template>
  <div id="cameraSettings">
    <div class="uk-grid uk-grid-divider uk-child-width-expand" uk-grid>
      <div class="uk-width-large">
        <h3>Manual camera settings</h3>
        <form @submit.prevent="applySettingsRequest" >
          <div class="uk-margin-small-bottom">
            <ul uk-accordion="multiple: true">
              <li class="uk-open">
                <a class="uk-accordion-title" href="#">Pi Camera Settings</a>
                <div class="uk-accordion-content">
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
                        step="0.0000000000000001"
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
                        step="0.0000000000000001"
                      />
                    </div>
                  </div>

                  <div v-if="picamera.awb_gains !== undefined">
                    <label class="uk-form-label" for="form-stacked-text" >
                      White Balance gains
                    </label>
                    <div class="uk-form-controls">
                      <label class="uk-form-label" >R:</label>
                      <input
                        v-model="picamera.awb_gains[0]"
                        class="uk-input uk-form-small"
                        type="number"
                        step="0.0000000000000001"
                      />
                      <label class="uk-form-label" >B:</label>
                      <input
                        v-model="picamera.awb_gains[1]"
                        class="uk-input uk-form-small"
                        type="number"
                        step="0.0000000000000001"
                      />
                    </div>
                  </div>
                </div>
              </li>

              <li class="uk-open">
                <a class="uk-accordion-title" href="#">Image Quality</a>
                <div class="uk-accordion-content">
                  <div class="uk-child-width-1-2" uk-grid>
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

                    <div v-if="stream_resolution !== undefined">
                      <label class="uk-form-label" for="form-stacked-text"
                        >Stream resolution</label
                      >
                      <select
                        v-model="stream_resolution"
                        class="uk-select uk-form-small"
                      >
                        <option
                          v-for="option in resolutionOptions"
                          :key="option.value[0]"
                          :value="option.value"
                        >
                          {{ option.text }}
                        </option>
                      </select>
                    </div>
                  </div>
                </div>
              </li>
              <li>
                <a class="uk-accordion-title" href="#">Advanced</a>
                <div class="uk-accordion-content">
                  <div v-if="mjpeg_bitrate !== undefined">
                    <label class="uk-form-label" for="form-stacked-text"
                      >Camera bitrate</label
                    >
                    <select
                      v-model="mjpeg_bitrate"
                      class="uk-select uk-form-small"
                    >
                      <option
                        v-for="option in bitrateOptions"
                        :key="option.value"
                        :value="option.value"
                      >
                        {{ option.text }}
                      </option>
                    </select>
                    <p class="uk-margin-remove">
                      This option sets the target bitrate for camera
                      recordings.<br />
                      <b
                        >Limiting bitrate may impact fast-autofocus
                        reliability.</b
                      >
                      However is guaranteed to fix the live stream disappearing
                      for some highly detailed samples.
                    </p>
                  </div>

                  <div
                    v-if="picamera.framerate !== undefined"
                    class="uk-margin-top"
                  >
                    <label class="uk-form-label" for="form-stacked-text"
                      >Camera framerate</label
                    >
                    <select
                      v-model="picamera.framerate"
                      class="uk-select uk-form-small"
                    >
                      <option
                        v-for="option in framerateOptions"
                        :key="option.value"
                        :value="option.value"
                      >
                        {{ option.text }}
                      </option>
                    </select>
                    <p class="uk-margin-remove">
                      This option sets the framerate of the Pi Camera video
                      encoder. The actual stream framerate is determined by
                      network speed, and is limited by the encoder framerate.<br />
                      <b
                        >Lowering framerate may impact fast-autofocus
                        accuracy.</b
                      >
                    </p>
                  </div>
                </div>
              </li>
            </ul>
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
        digital_gain: undefined,
        framerate: undefined,
        awb_gains: undefined
      },
      mjpeg_bitrate: undefined,
      stream_resolution: undefined,
      jpeg_quality: undefined,
      bitrateOptions: [
        { text: "Maximum (unlimited)", value: -1 },
        { text: "High (25Mbps)", value: 25000000 },
        { text: "Normal (17Mbps)", value: 17000000 },
        { text: "Low (5Mbps)", value: 5000000 },
        { text: "Very low (2.5Mbps)", value: 2500000 }
      ],
      resolutionOptions: [
        { text: "Higher (832, 624)", value: [832, 624] },
        { text: "Normal (640, 480)", value: [640, 480] }
      ],
      framerateOptions: [
        { text: "Normal (30fps)", value: 30 },
        { text: "Low (15fps)", value: 15 },
        { text: "Very low (10fps)", value: 10 }
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
          this.stream_resolution = cameraSettings.stream_resolution;
          // Get Pi Camera settings if they exist
          if (cameraSettings.picamera) {
            this.picamera.analog_gain = cameraSettings.picamera.analog_gain;
            this.picamera.digital_gain = cameraSettings.picamera.digital_gain;
            this.picamera.shutter_speed = cameraSettings.picamera.shutter_speed;
            this.picamera.framerate = cameraSettings.picamera.framerate;
            this.picamera.awb_gains = cameraSettings.picamera.awb_gains;
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
          stream_resolution: this.stream_resolution,
          picamera: {
            shutter_speed: parseFloat(this.picamera.shutter_speed),
            analog_gain: parseFloat(this.picamera.analog_gain),
            digital_gain: parseFloat(this.picamera.digital_gain),
            framerate: parseInt(this.picamera.framerate),
            awb_gains: [
              parseFloat(this.picamera.awb_gains[0]),
              parseFloat(this.picamera.awb_gains[1]),
            ],
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

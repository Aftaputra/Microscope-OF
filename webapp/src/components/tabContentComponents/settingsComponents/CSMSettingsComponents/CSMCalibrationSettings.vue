<template>
  <div id="CSMCalibrationSettings">
    <!--Show auto calibrate if default plugin is enabled-->
    <div v-if="'calibrate_xy' in actions" class="uk-margin-small">
      <taskSubmitter
        :button-primary="true"
        :can-terminate="false"
        :requires-confirmation="true"
        :confirmation-message="
          'Start recalibration of the stage to the camera? This may take a while, and the microscope will be locked during this time.'
        "
        :submit-url="thingUri + 'calibrate_xy'"
        :submit-label="'Auto-Calibrate using camera'"
        @response="onRecalibrateResponse"
        @error="modalError"
      />
    </div>
    <button
      v-if="'last_calibration' in properties"
      v-show="showExtraSettings"
      type="button"
      class="uk-button uk-button-default uk-width-1-1"
      @click="getCalibrationData()"
    >
      Download calibration data
    </button>
  </div>
</template>

<script>
import axios from "axios";
import taskSubmitter from "../../../genericComponents/taskSubmitter";

// Export main app
export default {
  name: "CSMCalibrationSettings",

  components: {
    taskSubmitter
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
      settings: null,
      actions: {},
      properties: {}
    };
  },

  computed: {
    thingUri: function() {
      return `${this.$store.getters.baseUri}/camera_stage_mapping/`;
    }
  },

  mounted() {
    this.updateActions();
  },

  methods: {
    getCalibrationData: async function() {
      try {
        let response = await axios.get(this.thingUri + "last_calibration");
        if (response.data == {}) {
          throw "No calibration data available.";
        }
        const data = JSON.stringify(response.data);
        const url = window.URL.createObjectURL(new Blob([data]));
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", "csm_calibration.json");
        document.body.appendChild(link);
        link.click();
      } catch (error) {
        this.modalError(error); // Let mixin handle error
      }
    },

    updateActions: async function() {
      try {
        let response = await axios.get(this.thingUri); // Get Thing Description
        this.actions = response.data.actions;
        this.properties = response.data.properties;
      } catch (error) {
        this.modalError(error); // Let mixin handle error
      }
    },

    onRecalibrateResponse: function() {
      this.modalNotify("Finished stage-to-camera calibration.");
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

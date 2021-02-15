<template>
  <div>
    <!--Show auto calibrate if default plugin is enabled-->
    <div v-if="'recalibrate' in recalibrationLinks" class="uk-margin-small">
      <taskSubmitter
        :can-terminate="false"
        :requires-confirmation="true"
        :confirmation-message="
          'Start recalibration? This may take a while, and the microscope will be locked during this time.'
        "
        :submit-url="recalibrationLinks.recalibrate.href"
        :submit-label="'Full Auto-Calibrate'"
        @response="onRecalibrateResponse"
        @error="modalError"
      >
      </taskSubmitter>
    </div>
    <div v-if="'auto_exposure_from_raw' in recalibrationLinks" class="uk-margin-small">
      <taskSubmitter
        :can-terminate="false"
        :requires-confirmation="false"
        :submit-url="recalibrationLinks.auto_exposure_from_raw.href"
        :submit-label="'Auto gain &amp; shutter speed'"
        @response="onRecalibrateResponse"
        @error="modalError"
      >
      </taskSubmitter>
    </div>
    <div v-if="'auto_white_balance_from_raw' in recalibrationLinks" class="uk-margin-small">
      <taskSubmitter
        :can-terminate="false"
        :requires-confirmation="false"
        :submit-url="recalibrationLinks.auto_white_balance_from_raw.href"
        :submit-label="'Auto white balance'"
        @response="onRecalibrateResponse"
        @error="modalError"
      >
      </taskSubmitter>
    </div>

    <div v-show="showExtraSettings" class="uk-child-width-expand">
      <button
        v-if="'flatten_lens_shading_table' in recalibrationLinks"
        class="uk-button uk-button-danger uk-width-1-1"
        @click="flattenLensShadingTableRequest"
      >
        Disable flat-field correction
      </button>
    </div>

    <div v-if="LstDownloadEnabled">
      <a
        class="uk-button uk-button-default uk-width-large uk-margin-small-top uk-align-center"
        :href="LstDownloadUri"
        download
        >Download Lens-Shading Table</a
      >
    </div>
  </div>
</template>

<script>
import axios from "axios";
import taskSubmitter from "../../../genericComponents/taskSubmitter";

// Export main app
export default {
  name: "CameraCalibrationSettings",

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
      recalibrationLinks: {},
      isCalibrating: false,
      LstDownloadEnabled: false
    };
  },

  computed: {
    pluginsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/extensions`;
    },
    LstDownloadUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/instrument/camera/lst`;
    }
  },

  mounted() {
    this.updateRecalibrationLinks();
    this.checkLstDownload();
  },

  methods: {
    updateRecalibrationLinks: function() {
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
            this.recalibrationLinks = foundExtension.links;
          } else {
            this.recalibrationLinks = {};
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    checkLstDownload: function() {
      axios
        .get(this.LstDownloadUri) // Get a list of plugins
        .then(response => {
          if (response.status === 200) {
            this.LstDownloadEnabled = true;
          } else {
            this.LstDownloadEnabled = false;
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    onRecalibrateResponse: function() {
      this.modalNotify("Finished recalibration.");
    },

    flattenLensShadingTableRequest: function() {
      axios.post(this.recalibrationLinks.flatten_lens_shading_table.href);
    },
    deleteLensShadingTableRequest: function() {
      axios.post(this.recalibrationLinks.delete_lens_shading_table.href);
    }
  }
};
</script>

<style lang="less"></style>

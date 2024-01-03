<template>
  <div>
    <!--Show auto calibrate if default plugin is enabled-->
    <div v-if="'full_auto_calibrate' in actions" class="uk-margin-small">
      <taskSubmitter
        :can-terminate="false"
        :requires-confirmation="true"
        :confirmation-message="
          'Start recalibration? This may take a while, and the microscope will be locked during this time.'
        "
        :submit-url="cameraUri + 'full_auto_calibrate'"
        :submit-label="'Full Auto-Calibrate'"
        @response="onRecalibrateResponse"
        @error="modalError"
      >
      </taskSubmitter>
    </div>
    <div v-if="'auto_expose_from_minimum' in actions" class="uk-margin-small">
      <taskSubmitter
        :can-terminate="false"
        :requires-confirmation="false"
        :submit-url="cameraUri + 'auto_expose_from_minimum'"
        :submit-label="'Auto gain &amp; shutter speed'"
        @response="onRecalibrateResponse"
        @error="modalError"
      >
      </taskSubmitter>
    </div>
    <div v-if="'calibrate_white_balance' in actions" class="uk-margin-small">
      <taskSubmitter
        :can-terminate="false"
        :requires-confirmation="false"
        :submit-url="cameraUri + 'calibrate_white_balance'"
        :submit-label="'Auto white balance'"
        @response="onRecalibrateResponse"
        @error="modalError"
      >
      </taskSubmitter>
    </div>
    <div v-if="'calibrate_lens_shading' in actions" class="uk-margin-small">
      <taskSubmitter
        :can-terminate="false"
        :requires-confirmation="true"
        :confirmation-message="
          'Is the microscope looking at an evenly illuminated, empty field of view? ' +
            'If not, the current image will show through in any images captured afterwards.'
        "
        :submit-url="cameraUri + 'calibrate_lens_shading'"
        :submit-label="'Auto flat field correction'"
        @response="onRecalibrateResponse"
        @error="modalError"
      >
      </taskSubmitter>
    </div>

    <div
      v-show="showExtraSettings"
      v-if="'flatten_lens_shading_table' in actions"
      class="uk-child-width-expand"
    >
      <taskSubmitter
        :can-terminate="false"
        :requires-confirmation="false"
        :submit-url="cameraUri + 'flat_lens_shading'"
        :submit-label="'Disable flat field correction'"
        @response="onRecalibrateResponse"
        @error="modalError"
      >
      </taskSubmitter>
    </div>
    <div
      v-show="showExtraSettings"
      v-if="'reset_lens_shading' in actions"
      class="uk-child-width-expand"
    >
      <taskSubmitter
        :can-terminate="false"
        :requires-confirmation="false"
        :submit-url="cameraUri + 'reset_lens_shading'"
        :submit-label="'Reset flat field correction'"
        @response="onRecalibrateResponse"
        @error="modalError"
      >
      </taskSubmitter>
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
    },
    cameraUri: {
      type: String,
      required: true
    }
  },

  data: function() {
    return {
      actions: {},
      isCalibrating: false,
      LstDownloadEnabled: false
    };
  },

  mounted() {
    this.updateActions();
  },

  methods: {
    updateActions: async function() {
      try {
        let response = await axios.get(this.cameraUri); // Get the thing description
        let td = response.data;
        this.actions = td.actions;
      } catch (error) {
        this.modalError(error); // Let mixin handle error
      }
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

<template>
  <div>
    <!--Show auto calibrate if default plugin is enabled-->
    
    <div 
      v-for="(action, index) in secondaryCalibrationActions"
      class="uk-child-width-expand"
      :key = "'primary_cal' + index"
    >
      <action-button
        :can-terminate="action.can_terminate"
        :requires-confirmation="action.requires_confirmation"
        :thing="action.thing"
        :action="action.action"
        :submit-label="action.submit_label"
        @response="onRecalibrateResponse"
        @error="modalError"
      />
    </div>
    <div v-if="showExtraSettings">
      <div 
        v-for="(action, index) in primaryCalibrationActions"
        class="uk-child-width-expand"
        :key = "'secondary_cal' + index"
      >
        <action-button
          :can-terminate="action.can_terminate"
          :requires-confirmation="action.requires_confirmation"
          :thing="action.thing"
          :action="action.action"
          :submit-label="action.submit_label"
          @response="onRecalibrateResponse"
          @error="modalError"
        />
      </div>
    </div>
  </div>
</template>

<script>
import ActionButton from "../../../labThingsComponents/actionButton.vue";

// Export main app
export default {
  name: "CameraCalibrationSettings",

  components: {
    ActionButton
  },

  data() {
    return {
      primaryCalibrationActions: [],
      secondaryCalibrationActions: []
    };
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

  computed: {
    actions() {
      return this.$store.getters["wot/thingDescription"]("camera").actions;
    }
  },

  async created() {
    this.primaryCalibrationActions = await this.readThingProperty("camera", "primary_calibration_actions");
    this.secondaryCalibrationActions = await this.readThingProperty("camera", "secondary_calibration_actions");
  },

  methods: {
    onRecalibrateResponse: function() {
      this.modalNotify("Finished recalibration.");
    }
  }
};
</script>

<style lang="less"></style>

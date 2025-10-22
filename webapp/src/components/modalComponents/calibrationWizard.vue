<template>
  <div id="modal-example" ref="calibrationModalEl" uk-modal="bg-close: false;">
    <div class="uk-modal-dialog uk-modal-body">
      <h2 class="uk-modal-title">Microscope Calibration</h2>
      

      <p class="uk-text-right">
        <button
          v-show="stepValue == 0"
          class="uk-button uk-button-default uk-modal-close"
          type="button"
        >
          Cancel
        </button>
        <button
          v-show="stepValue == 4"
          class="uk-button uk-button-default"
          type="button"
          @click="restart()"
        >
          Restart
        </button>
        <button
          v-show="stepValue < 4"
          class="uk-button uk-button-primary uk-margin-left"
          type="button"
          @click="increment()"
        >
          Next
        </button>
        <button
          v-show="stepValue == 4"
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

export default {
  name: "calibrationWizard",

  components: {},

  data: function() {
    return {
      stepValue: 0,
      isNeeded: undefined,
      calibrateableThings: []
    };
  },

  mounted() {
    this.$refs["calibrationModalEl"].addEventListener("hidden", this.onHide);
    // Check which Things are available on mount.
    const thingsToCheck = [
      "camera",
      "camera_stage_mapping"
    ];
    this.calibrateableThings = thingsToCheck.filter(name => this.thingAvailable(name));
  },

  methods: {
    /**
     * Checks all calibratable things to see if any require calibration.
     *
     * Iterates over `this.calibrateableThings` (set during mounted()) and reads the
     * `calibration_required` property.
     * 
     * Returns `true` if any Thing reports that calibration is required.
     *
     */
    async check_if_needed() {
      let wizardNeeded = false;
      let thingNeedsCal = false;

      for (const name of this.calibrateableThings) {
        try {
          thingNeedsCal = await this.readThingProperty(name, "calibration_required");
        } catch (e) {
          console.error(`${name}: missing calibration_required property`, e);
          thingNeedsCal = false;
        }

        // OR it into the function-level flag
        wizardNeeded = wizardNeeded || thingNeedsCal;
      }

      return wizardNeeded;
    },

    show_if_needed: async function() {
      // Check if the camera and stage are calibrated, if they can be
      let needed = await this.check_if_needed()

      // Check if this calibration wizard can actually do anything useful
      if (needed) {
        this.stepValue = 0;
        this.show()
      } else {
        // If not useful, we just return the onClose event immediately
        this.onHide();
      }
    },

    // Forces modal to show on button press
    force_show: function() {
      this.stepValue = 1;
      this.force = true
      this.show()
    },

    restart: function() {
      if (this.force == true){
        this.stepValue = 1
      } else {
        this.stepValue = 0
      }
    },

    show: function() {
      // Show the modal element
      var el = this.$refs["calibrationModalEl"];
      this.showModalElement(el); // Calls the mixin
    },

    hide: function() {
      // Show the modal
      var el = this.$refs["calibrationModalEl"];
      this.hideModalElement(el); // Calls the mixin
    },

    onHide: function() {
      this.$emit("onClose");
    },

    decrement: function() {
      if (this.stepValue > 0) {
        this.stepValue = this.stepValue - 1;
      }
    },

    increment: function() {
      // Upper bound on section number
      if (this.stepValue < 4) {
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
}
.action-button-container {
  display: flex;
  flex-direction: row;   /* Stack vertically */
  justify-content: center;  /* Left align */
  gap: 8px;                  /* Small space between buttons */
  margin-top: 4px;           /* Gap from image */
}
>>> .moveZ .uk-button.uk-width-1-1 {
  line-height: 50px;
  font-size: 50px !important;
  height: 60px; 
  padding-bottom: 46px;
  margin: 0;                 /* Remove default margin */
  width: 120px;
  min-width: 80px;
}
</style>

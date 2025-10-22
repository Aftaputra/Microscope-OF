<template>
  <div id="modal-example" ref="calibrationModalEl" uk-modal="bg-close: false;">
    <div class="uk-modal-dialog uk-modal-body">
      <h2 class="uk-modal-title">Microscope Calibration</h2>

      <component
        v-if="currentTask"
        :is="currentTask.component"
        :key="taskIndex"
        v-bind="currentTask.props"
        :first="isFirstTask"
        :final="isFinalTask"
        :startOnLast="movingBackward"
        @next="nextTask"
        @back="previousTask"
      />
      
    </div>
  </div>
</template>

<script>
import singleStepTask from "./calibrationWizardComponents/singleStepTask.vue";
import welcomeStep from "./calibrationWizardComponents/welcomeStep.vue";
import cameraCalibrationTask from "./calibrationWizardComponents/cameraCalibrationTask.vue";
import cameraStageMappingTask from "./calibrationWizardComponents/cameraStageMappingTask.vue";
import finalStep from "./calibrationWizardComponents/finalStep.vue";

export default {
  name: "calibrationWizard",

  components: {},

  data: function() {
    return {
      isNeeded: undefined,
      calibrateableThings: [],
      tasks: [],
      taskIndex: 0,
      movingBackward: false
    };
  },

  computed: {
    currentTask() {
      return this.tasks[this.taskIndex] || null;
    },
    isFirstTask() {
      return this.taskIndex === 0;
    },
    isFinalTask() {
      return this.taskIndex === this.tasks.length - 1;
    }
  },

  mounted() {
    this.$refs["calibrationModalEl"].addEventListener("hidden", this.onHide);
    // Check which Things are available on mount.
    const thingsToCheck = [
      "camera",
      "camera_stage_mapping"
    ];
    this.calibrateableThings = thingsToCheck.filter(name => this.thingAvailable(name));
    this.tasks = [
      {component: singleStepTask, props: {stepComponent: welcomeStep}},
      {component: cameraCalibrationTask},
      {component: cameraStageMappingTask},
      {component: singleStepTask, props: {stepComponent: finalStep}},
    ]
  },

  methods: {
    /**
     * Check all calibratable Things to see if any require calibration.
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

    resetData: function() {
      this.movingBackward = false;
      this.taskIndex = 0;
    },

    show_if_needed: async function() {
      // Check if the calibration modal is needed, and only show it if it is.
      let needed = await this.check_if_needed()

      // Check if this calibration wizard can actually do anything useful
      if (needed) {
        this.resetData();
        this.show();
      } else {
        // If not needed, we just return the onClose event immediately
        this.onHide();
      }
    },

    // Forces modal to show on button press
    force_show: function() {
      this.resetData();
      this.show();
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

    /*
     * Move to the previous task.
     */
    previousTask: function() {
      this.movingBackward = true;
      if (this.taskIndex > 0) {
        this.taskIndex = this.taskIndex - 1;
      }
    },

    /*
     * Move to the next task or close the modal if this is the final task.
     */
    nextTask: function() {
      this.movingBackward = false;
      if (this.taskIndex < this.tasks.length - 1) {
        this.taskIndex = this.taskIndex + 1;
        return true;
      }
      else {
        this.hide();
      }
    }
  }
};
</script>

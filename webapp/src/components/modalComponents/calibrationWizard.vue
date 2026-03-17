<template>
  <div id="modal-example" ref="calibrationModalEl" uk-modal="bg-close: false; esc-close:false;">
    <div class="uk-modal-dialog uk-modal-body">
      <!-- Get the style from uk-close, but use stop.prevent to avoid it actually closing -->
      <button
        type="button"
        class="uk-modal-close-default"
        uk-close
        @click.stop.prevent="confirmClose"
      ></button>
      <h2 class="uk-modal-title">Microscope Calibration</h2>

      <component
        v-bind="currentTask.props"
        :is="currentTask.component"
        v-if="currentTask"
        :key="taskIndex"
        :first="isFirstTask"
        :final="isFinalTask"
        :start-on-last="movingBackward"
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
import { markRaw } from "vue";

export default {
  name: "CalibrationWizard",

  components: {},

  emits: ["onClose"],

  data: function () {
    return {
      isNeeded: undefined,
      availableCalibrationTasks: {},
      tasks: [],
      taskIndex: 0,
      movingBackward: false,
      modalOpen: false,
      confirmingClose: false,
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
    },
  },

  mounted() {
    this.$refs["calibrationModalEl"].addEventListener("hidden", this.onHide);
    // Check which Things are available on mount.
    const allCalibrationTasks = {
      camera: cameraCalibrationTask,
      camera_stage_mapping: cameraStageMappingTask,
    };
    this.availableCalibrationTasks = Object.fromEntries(
      Object.entries(allCalibrationTasks).filter(([thing]) => this.thingAvailable(thing)),
    );
  },

  methods: {
    /**
     * Check all calibratable Things to see which require calibration.
     *
     * Iterates over `this.availableCalibrationTasks` (set during mounted()) and reads the
     * `calibration_required` property.
     *
     * Returns a list of thing names that report calibration is required.
     */
    async check_things_needing_calibration() {
      const needsCalibration = [];
      const calibrateableThings = Object.keys(this.availableCalibrationTasks);

      for (const name of calibrateableThings) {
        if (this.thingPropertyAvailable(name, "calibration_required")) {
          const thingNeedsCal = await this.readThingProperty(name, "calibration_required");
          if (thingNeedsCal) {
            needsCalibration.push(name);
          }
        }
      }

      return needsCalibration;
    },

    resetData: function () {
      this.movingBackward = false;
      this.taskIndex = 0;
    },

    /**
     * Create the calibration wizard task list dynamically.
     */
    create_task_list: function (thingsToCal, includeWelcome = true) {
      const tasks = [];

      // Optionally include the welcome screen
      if (includeWelcome) {
        tasks.push({
          component: markRaw(singleStepTask),
          props: { stepComponent: welcomeStep },
        });
      }

      // Add calibration task for each thing
      for (const thing of thingsToCal) {
        const taskComponent = this.availableCalibrationTasks[thing];
        tasks.push({ component: markRaw(taskComponent), props: {} });
      }

      // Always include the final step
      tasks.push({
        component: markRaw(singleStepTask),
        props: { stepComponent: finalStep },
      });

      this.tasks = tasks;
    },

    show_if_needed: async function () {
      // Check if the calibration modal is needed, and only show it if it is.
      let thingsToCal = await this.check_things_needing_calibration();
      const needed = thingsToCal.length > 0;

      // Check if this calibration wizard can actually do anything useful
      if (needed) {
        this.resetData();
        this.create_task_list(thingsToCal);
        this.show();
      } else {
        // If not needed, we just return the onClose event immediately
        this.onHide();
      }
    },

    // Forces modal to show on button press
    force_show: function () {
      const allThings = Object.keys(this.availableCalibrationTasks);

      this.resetData();
      this.create_task_list(allThings, false);
      this.show();
    },

    show: function () {
      this.modalOpen = true;
      window.addEventListener("keydown", this.handleKeydown);

      // Show the modal element
      var el = this.$refs["calibrationModalEl"];
      this.showModalElement(el); // Calls the mixin
    },

    hide: function () {
      this.modalOpen = false;
      window.removeEventListener("keydown", this.handleKeydown);

      // Show the modal
      var el = this.$refs["calibrationModalEl"];
      this.hideModalElement(el); // Calls the mixin
    },

    onHide: function () {
      this.$emit("onClose");
    },

    handleKeydown(event) {
      if (event.key === "Escape" && !event.repeat && this.modalOpen && !this.confirmingClose) {
        event.preventDefault();
        this.confirmClose();
      }
    },

    confirmClose() {
      if (this.confirmingClose) return;
      this.confirmingClose = true;
      let confirmationMessage =
        "Close calibration wizard?<br><br>This can be re-opened from the Settings tab at any time.";
      // Use standard modal confirmation
      this.modalConfirm(confirmationMessage)
        .then(
          () => {
            // User clicked YES → hide modal
            this.hide();
          },
          () => {
            // User clicked NO → do nothing, modal stays open
          },
        )
        .finally(() => {
          this.confirmingClose = false; // reset flag when confirmation modal is gone
        });
    },

    /*
     * Move to the previous task.
     */
    previousTask: function () {
      this.movingBackward = true;
      if (this.taskIndex > 0) {
        this.taskIndex = this.taskIndex - 1;
      }
    },

    /*
     * Move to the next task or close the modal if this is the final task.
     */
    nextTask: function () {
      this.movingBackward = false;
      if (this.taskIndex < this.tasks.length - 1) {
        this.taskIndex = this.taskIndex + 1;
        return true;
      } else {
        this.hide();
      }
    },
  },
};
</script>

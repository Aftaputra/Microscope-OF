<template>
  <calibrationWizardTask
    title="Camera Calibration"
    :first="first"
    :final="final"
    :start-on-last="startOnLast"
    :steps="steps"
    @next="$emit('next')"
    @back="$emit('back')"
  />
</template>

<script>
import calibrationWizardTask from "./calibrationWizardTask.vue";
import camCalibrationExplanation from "./cameraCalibrationSteps/camCalibrationExplanation.vue";
import cameraMainCalibrationStep from "./cameraCalibrationSteps/cameraMainCalibrationStep.vue";
import { markRaw } from "vue";
import CameraFocusStep from "./cameraCalibrationSteps/cameraFocusStep.vue";

export default {
  name: "CameraCalibrationTask",
  components: {
    calibrationWizardTask,
  },

  props: {
    // Standard calibrationWizardTask props below:
    first: Boolean,
    final: Boolean,
    startOnLast: {
      type: Boolean,
      default: false,
    },
  },

  emits: ["next", "back"],

  data: function () {
    return {
      steps: [
        { component: markRaw(camCalibrationExplanation) },
        { component: markRaw(CameraFocusStep) },
        { component: markRaw(cameraMainCalibrationStep) },
      ],
    };
  },
};
</script>

<template>
  <calibrationWizardTask
    title="Camera-Stage Mapping"
    :first="first"
    :final="final"
    :startOnLast="startOnLast"
    :steps="steps"
    @next="$emit('next')"
    @back="$emit('back')"
  />
</template>

<script>
import calibrationWizardTask from "./calibrationWizardTask.vue";
import csmExplanation from "./csmSteps/csmExplanation.vue";
import focusStep from "./csmSteps/focusStep.vue";
import runCsmStep from "./csmSteps/runCsmStep.vue";

export default {
  name: "cameraCalibrationTask",
  components: { calibrationWizardTask },
  props: {
    // Standard calibrationWizardTask props below:
    first: Boolean,
    final: Boolean,
    startOnLast: {
      type: Boolean,
      default: false
    }
  },

  data: function() {
    return {
      steps: [
        { component: csmExplanation },
        { component: focusStep },
        { component: runCsmStep }
      ]
    };
  }
};
</script>

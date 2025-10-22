<template>
  <calibrationWizardTask
    :title="title"
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

export default {
  name: "singleStepTask",
  components: { calibrationWizardTask },
  props: {
    // This must be sent
    stepComponent: {
      type: Object,
      required: true
    },
    // This is optional.
    stepProps: {
      type: Object,
      default: () => ({})
    },
    // Standard calibrationWizardTask props below:
    title: {
      type: String,
      default: null
    },
    first: Boolean,
    final: Boolean,
    startOnLast: {
      type: Boolean,
      default: false
    }
  },

  data: function() {
    return {
      steps: [{ component: this.stepComponent, props: this.stepProps }]
    };
  }
};
</script>

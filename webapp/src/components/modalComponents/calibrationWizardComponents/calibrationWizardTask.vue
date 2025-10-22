<!-- The base component for a wizard task.

Do not import this directly into CalibrationWizard as the list of steps and props
will be confusing.

A task should be used for higher level groupings of individual steps in the wizard,
such as calibrating a Thing.

Tasks can be divided into multiple steps.

-->
<template>
  <div>
    <component
      v-if="currentStep"
      :is="currentStep.component"
      :key="stepIndex"
      v-bind="currentStep.props"
    />
    <p class="uk-text-right">
      <button
        v-if="showBackButton"
        class="uk-button uk-button-default"
        type="button"
        @click="previousStep"
      >
        Back
      </button>
      <button
        class="uk-button uk-button-primary uk-margin-left"
        type="button"
        @click="nextStep"
      >
        {{ nextButtonText }}
      </button>
    </p>
  </div>
</template>

<script>

export default {
  name: "calibrationWizardTask",

  props: {
    first: Boolean,
    final: Boolean,
    startOnLast: {
      type: Boolean,
      default: false
    },
    steps: {
      type: Array,
      required: true
    }
  },

  data() {
    return {
      stepIndex: this.startOnLast ? this.steps.length-1 : 0
    };
  },

  mounted() {
    console.log("Steps received:", this.steps);
  },

  computed: {
    currentStep() {
      return this.steps[this.stepIndex] || null;
    },
    showBackButton() {
      return !this.first || this.stepIndex > 0;
    },
    nextButtonText() {
      return this.final && this.stepIndex === this.steps.length - 1 ? "Finish" : "Next";
    }
  },

  methods: {
    /*
     * Move to the previous step in this task, or the previous task if first step.
     */
    previousStep: function() {
      if (this.stepIndex > 0) {
        this.stepIndex = this.stepIndex - 1;
      } else {
        this.$emit("back");
      }
    },

    /*
     * Move to the next step in this task, or the next task if final step.
     */
    nextStep: function() {
      if (this.stepIndex < this.steps.length - 1) {
        this.stepIndex = this.stepIndex + 1;
        return true;
      } else {
        this.$emit("next");
      }
    }
  }
}
</script>

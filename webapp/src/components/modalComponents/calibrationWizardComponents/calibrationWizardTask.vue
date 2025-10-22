<template>
  <div>
    <p>{{num}}.{{stepIndex}}</p>
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
    num: Number,
    first: Boolean,
    final: Boolean,
    startOnLast: {
      type: Boolean,
      default: false
    },
    steps: {
      type: Number,
      default: 2
    }
  },

  data() {
    return {
      stepIndex: this.startOnLast ? this.steps-1 : 0
    };
  },

  computed: {
    showBackButton() {
      return !this.first || this.stepIndex > 0;
    },
    nextButtonText() {
      return this.final && this.stepIndex === this.steps - 1 ? "Finish" : "Next";
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
      if (this.stepIndex < this.steps - 1) {
        this.stepIndex = this.stepIndex + 1;
        return true;
      } else {
        this.$emit("next");
      }
    }
  }
}
</script>

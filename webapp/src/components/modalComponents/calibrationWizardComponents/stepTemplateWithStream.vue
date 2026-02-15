<template>
  <div>
    <slot></slot>
    <miniStreamDisplay class="mini-preview" />
    <slot name="below-stream"></slot>
  </div>
</template>

<script>
import miniStreamDisplay from "../../genericComponents/miniStreamDisplay.vue";

export default {
  name: "StepTemplateWithStream",

  components: {
    miniStreamDisplay,
  },
};
</script>

<style scoped>
.mini-preview {
  width: 75%;
  margin-left: auto;
  margin-right: auto;
}
</style>

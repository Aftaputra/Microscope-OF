<template>
  <stepTemplateWithStream>
    <p>Use the buttons below to bring the sample into focus.</p>
    <p>You may also adjust the z position with <b>page up</b> and <b>page down</b>.</p>
    <template #below-stream>
      <stageControlButtons :show-dpad="false" />
    </template>
  </stepTemplateWithStream>
</template>

<script>
import stepTemplateWithStream from "../stepTemplateWithStream.vue";
import stageControlButtons from "@/components/tabContentComponents/controlComponents/stageControlButtons.vue";
export default {
  name: "CameraMainCalibrationStep",

  components: {
    stepTemplateWithStream,
    stageControlButtons,
  },
};
</script>
<style scoped></style>

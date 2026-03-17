<template>
  <stepTemplateWithStream>
    <ul>
      <li>
        Move your slide to an empty area, ideally looking through the coverslip if your slide has
        one.
      </li>
      <li>
        Use the buttons below or Page Up/Down to defocus slightly, to make sure no features are
        visible.
      </li>
    </ul>
    <template #below-stream>
      <stageControlButtons :show-dpad="false" />
    </template>
  </stepTemplateWithStream>
</template>

<script>
import stepTemplateWithStream from "../stepTemplateWithStream.vue";
import stageControlButtons from "@/components/tabContentComponents/controlComponents/stageControlButtons.vue";
export default {
  name: "CameraFocusStep",

  components: {
    stepTemplateWithStream,
    stageControlButtons,
  },
};
</script>
<style scoped></style>

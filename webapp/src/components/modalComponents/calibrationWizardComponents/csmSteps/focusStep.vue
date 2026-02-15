<template>
  <stepTemplateWithStream>
    <p>Use the buttons below to bring the sample into focus.</p>
    <p>You may also adjust the z position with <b>page up</b> and <b>page down</b>.</p>
    <template #below-stream>
      <div class="action-button-container">
        <action-button
          class="moveZ"
          thing="stage"
          action="move_relative"
          :button-primary="false"
          :submit-data="{ x: 0, y: 0, z: -100 }"
          :submit-label="' - '"
          :can-terminate="false"
        />
        <action-button
          class="moveZ"
          thing="stage"
          action="move_relative"
          :button-primary="false"
          :submit-data="{ x: 0, y: 0, z: 100 }"
          :submit-label="'+'"
          :can-terminate="false"
        />
      </div>
    </template>
  </stepTemplateWithStream>
</template>

<script>
import stepTemplateWithStream from "../stepTemplateWithStream.vue";
import ActionButton from "../../../labThingsComponents/actionButton.vue";
// vue3 migration

export default {
  name: "CameraMainCalibrationStep",

  components: {
    stepTemplateWithStream,
    ActionButton,
  },
};
</script>
<style scoped>
.action-button-container {
  display: flex;
  flex-direction: row; /* Stack vertically */
  justify-content: center; /* Left align */
  gap: 8px; /* Small space between buttons */
  margin-top: 4px; /* Gap from image */
}
.moveZ :deep(.uk-button.uk-width-1-1) {
  line-height: 50px;
  font-size: 50px !important;
  height: 60px;
  padding-bottom: 46px;
  margin: 0; /* Remove default margin */
  width: 120px;
  min-width: 80px;
}
</style>

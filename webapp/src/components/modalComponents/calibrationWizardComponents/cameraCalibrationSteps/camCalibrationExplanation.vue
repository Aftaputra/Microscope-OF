<template>
  <stepTemplateWithStream>
    <div>
      <p>
        <b> Before starting camera calibration: </b>
      </p>
      <ul class="uk-list uk-list-bullet">
        <li>Ensure your illumination is on, well focused, and centred.</li>
        <li>Insert a slide with some empty areas.</li>
        <li>If your slide has no empty areas, remove it and instead calibrate with no sample.</li>
      </ul>
    </div>
  </stepTemplateWithStream>
</template>

<script>
import stepTemplateWithStream from "../stepTemplateWithStream.vue";
export default {
  name: "CamExplanationStep",

  components: {
    stepTemplateWithStream,
  },
};
</script>
<style scoped></style>

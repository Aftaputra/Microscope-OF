<template>
  <div id="paneControl" class="uk-padding-small">
    <positionControl v-if="stageAvailable" />
    <illuminationControl v-if="illuminationAvailable" />
    <autofocusControl v-if="autofocusAvailable" />
    <captureControl />
  </div>
</template>

<script>
import captureControl from "./captureControl.vue";
import positionControl from "./positionControl.vue";
import autofocusControl from "./autofocusControl.vue";
import illuminationControl from "./illuminationControl.vue";

export default {
  name: "PaneControl",
  components: {
    captureControl,
    positionControl,
    autofocusControl,
    illuminationControl,
  },
  computed: {
    stageAvailable() {
      return this.thingAvailable("stage");
    },
    autofocusAvailable() {
      return this.thingAvailable("autofocus");
    },
    illuminationAvailable() {
      return this.thingAvailable("illumination");
    },
  },
};
</script>
<template>
  <div class="uk-flex uk-flex-column uk-flex-center uk-height-1-1">
    <div v-if="waiting" class="uk-align-center uk-text-center">
      <div uk-spinner="ratio: 3"></div>
      <p>Loading...</p>
    </div>
    <span class="material-symbols-outlined uk-align-center error-icon">error_outline</span>
    <div v-if="error" class="uk-align-center">
      {{ error }}
    </div>
    <div class="uk-align-center">
      <devTools class="uk-width-medium"></devTools>
    </div>
  </div>
</template>

<script>
import devTools from "./tabContentComponents/aboutComponents/devTools.vue";
import { mapWritableState } from "pinia";
import { useSettingsStore } from "@/stores/settings.js";

// Export main app
export default {
  name: "LoadingContent",

  components: {
    devTools,
  },

  computed: {
    ...mapWritableState(useSettingsStore, ["error", "waiting"]),
  },
};
</script>

<style scoped lang="less">
.error-icon {
  font-size: 120px;
}
</style>

<template>
  <div>
    <appSettings />
    <streamSettings />
  </div>
</template>

<script>
import appSettings from "./displaySetttingsComponents/appSettings.vue";
import streamSettings from "./displaySetttingsComponents/streamSettings.vue";
import { markRaw } from "vue";

// Export main app
export default {
  name: "DisplaySettings",

  components: {
    streamSettings: markRaw(streamSettings),
    appSettings: markRaw(appSettings),
  },
};
</script>

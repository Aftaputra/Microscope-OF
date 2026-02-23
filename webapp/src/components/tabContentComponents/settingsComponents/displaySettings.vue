<template>
  <div>
    <appSettings />
    <streamSettings />
  </div>
</template>

<script>
import appSettings from "./displaySettingsComponents/appSettings.vue";
import streamSettings from "./displaySettingsComponents/streamSettings.vue";

// Export main app
export default {
  name: "DisplaySettings",

  components: {
    streamSettings,
    appSettings,
  },
};
</script>

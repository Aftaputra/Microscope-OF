<template>
  <div id="settingsDisplay" class="uk-padding">
    <div class="uk-child-width-expand@m" uk-grid>
      <div>
        <h3>System settings</h3>
        <appSettings />
        <streamSettings />
      </div>
      <div v-if="$store.getters.ready">
        <h3>Camera settings</h3>
        <cameraSettings />
      </div>
      <div v-if="$store.getters.ready">
        <h3>Microscope settings</h3>
        <microscopeSettings />
      </div>
    </div>
  </div>
</template>

<script>
import streamSettings from "./settingsComponents/streamSettings.vue";
import microscopeSettings from "./settingsComponents/microscopeSettings.vue";
import cameraSettings from "./settingsComponents/cameraSettings.vue";
import appSettings from "./settingsComponents/appSettings.vue";

// Export main app
export default {
  name: "SettingsDisplay",

  components: {
    streamSettings,
    cameraSettings,
    microscopeSettings,
    appSettings
  }
};
</script>

<style lang="less"></style>

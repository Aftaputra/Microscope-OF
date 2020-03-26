<template>
  <div id="settingsDisplay" class="uk-padding uk-height-1-1">
    <div class="uk-height-1-1 uk-child-width-expand@m" uk-grid>
      <div class="uk-padding-remove">
        <div class="settings-pane uk-padding-small">
          <h3>System settings</h3>
          <appSettings />
          <hr />
          <streamSettings />
        </div>
      </div>
      <div class="uk-padding-remove">
        <div v-if="$store.getters.ready" class="settings-pane uk-padding-small">
          <h3>Camera settings</h3>
          <cameraSettings />
        </div>
      </div>
      <div class="uk-padding-remove">
        <div v-if="$store.getters.ready" class="settings-pane uk-padding-small">
          <h3>Camera/stage mapping settings</h3>
          <cameraStageMappingSettings />
        </div>
      </div>
      <div class="uk-padding-remove">
        <div v-if="$store.getters.ready" class="settings-pane uk-padding-small">
          <h3>Microscope settings</h3>
          <microscopeSettings />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import streamSettings from "./settingsComponents/streamSettings.vue";
import microscopeSettings from "./settingsComponents/microscopeSettings.vue";
import cameraSettings from "./settingsComponents/cameraSettings.vue";
import appSettings from "./settingsComponents/appSettings.vue";
import cameraStageMappingSettings from "./settingsComponents/cameraStageMappingSettings.vue";

// Export main app
export default {
  name: "SettingsDisplay",

  components: {
    streamSettings,
    cameraSettings,
    microscopeSettings,
    cameraStageMappingSettings,
    appSettings
  }
};
</script>

<style lang="less">
.settings-pane {
  border-width: 0 1px 0 0;
  border-style: solid;
  border-color: rgba(180, 180, 180, 0.25);
  min-height: 100%;
}
</style>

<template>
  <div id="streamSettings" class="uk-width-large">
    <div>
      <h3>Stream Settings</h3>
      <label
        ><input v-model="disableStream" class="uk-checkbox" type="checkbox" /> Disable Web
        Stream</label
      >
      <p class="uk-margin-small">This will disable the embedded web stream of the camera.</p>
    </div>
  </div>
</template>

<script>
import { mapState } from "pinia";
import { useSettingsStore } from "@/stores/settings.js";

// Export main app
export default {
  name: "StreamSettings",

  data: function () {
    return {};
  },

  computed: {
    ...mapState(useSettingsStore, ["disableStream"]),
    disableStream: {
      get() {
        return this.disableStream;
      },
      set(value) {
        this.disableStream = value;
      },
    },
  },
};
</script>

<style lang="less"></style>

<template>
  <div>
    <form class="uk-form-stacked" action="" method="GET" @submit="overrideAPIHost">
      <label class="uk-form-label">Override API origin</label>
      <input v-model="overrideOrigin" name="overrideOrigin" class="uk-input" type="text" />
      <label class="uk-form-label">
        <input v-model="reloadWhenOverridingOrigin" class="uk-checkbox" type="checkbox" />
        Reload web app with new origin
      </label>
      <button class="uk-button uk-button-default uk-margin-small">Apply</button>
    </form>
  </div>
</template>

<script>
import { mapWritableState } from "pinia";
import { useSettingsStore } from "@/stores/settings.js";

export default {
  name: "DevTools",

  data() {
    return {
      reloadWhenOverridingOrigin: true,
    };
  },

  computed: {
    ...mapWritableState(useSettingsStore, ["overrideOrigin", "origin"]),
  },

  methods: {
    overrideAPIHost(event) {
      if (!this.reloadWhenOverridingOrigin) {
        this.origin = this.overrideOrigin;
        event.preventDefault();
      }
    },
  },
};
</script>

<style scoped lang="less">
.error-icon {
  font-size: 120px;
}
</style>

<template>
  <div id="appSettings">
    <p>
      <label
        ><input v-model="darkMode" class="uk-checkbox" type="checkbox" /> Enable
        dark theme</label
      >
    </p>
  </div>
</template>

<script>
// Export main app
export default {
  name: "AppSettings",

  data: function() {
    return {};
  },

  computed: {
    darkMode: {
      get() {
        return this.$store.state.globalSettings.darkMode;
      },
      set(value) {
        this.$store.commit("changeSetting", ["darkMode", value]);
      }
    }
  },

  watch: {
    darkMode() {
      console.log("Saving darkmode setting");
      this.setLocalStorageObj("darkMode", this.darkMode);
    }
  },

  mounted() {
    // Try loading settings from localStorage. If null, don't change.
    this.darkMode = this.getLocalStorageObj("darkMode") || this.darkMode;
  }
};
</script>

<style lang="less"></style>

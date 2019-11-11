<template>
  <div id="app" :class="handleTheme">
    <!-- Grid managing whole app -->
    <div
      uk-grid
      class="uk-height-1-1 uk-margin-remove uk-padding-remove"
      margin="0"
    >
      <panelLeft />
      <panelRight />
    </div>
  </div>
</template>

<script>
// Import components
import panelLeft from "./components/panelLeft.vue";
import panelRight from "./components/panelRight.vue";

// Export main app
export default {
  name: "App",

  components: {
    panelRight,
    panelLeft
  },

  data: function() {
    return {};
  },

  computed: {
    handleTheme: function() {
      return {
        "uk-light": this.$store.state.globalSettings.darkMode,
        "uk-background-secondary": this.$store.state.globalSettings.darkMode
      };
    }
  },

  created: function() {
    window.addEventListener("beforeunload", this.handleExit);
  },

  methods: {
    handleExit: function() {
      console.log("Triggered beforeunload");
      this.$root.$emit("globalTogglePreview", false);
    }
  }
};
</script>

<style lang="less">
// Basic UIkit CSS
@import "../node_modules/uikit/src/less/uikit.less";
// Custom UIkit CSS modifications
@import "./assets/less/theme.less";

// We override the custom-electron-titlebar z-index
// UIKit lightbox must be able to draw over the titlebar
// as it currently always spawns at the root of the DOM
.titlebar,
.titlebar > * {
  z-index: 1000 !important;
}

#app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: left;
  height: 100%;
}

body,
html {
  height: 100%;
  overflow: hidden;
}

.uk-disabled {
  pointer-events: none;
  opacity: 0.4;
}
</style>

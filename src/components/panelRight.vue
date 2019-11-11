<template>
  <!-- Tabbed panel for gallery and live views -->
  <div
    id="panel-right"
    class="uk-flex uk-flex-column uk-margin-remove uk-padding-remove uk-width-expand uk-height-1-1"
  >
    <ul
      id="tabContainer"
      class="uk-flex-none uk-flex-center uk-margin-remove-bottom uk-text-center"
      uk-tab="swiping: false"
    >
      <li><a href="#" uk-switcher-item="connect">Connect</a></li>
      <li :class="{ 'uk-disabled': !this.$store.getters.ready }">
        <a href="#" uk-switcher-item="preview">Live</a>
      </li>
      <li :class="{ 'uk-disabled': !this.$store.getters.ready }">
        <a href="#" uk-switcher-item="gallery">Gallery</a>
      </li>
    </ul>
    <ul class="uk-switcher uk-flex uk-flex-1 uk-overflow-auto">
      <li id="connectDisplayTab" class="uk-height-1-1 uk-width-1-1">
        <connectDisplay />
      </li>
      <li id="streamDisplayTab" class="uk-height-1-1 uk-width-1-1 clickableTab">
        <streamDisplay />
      </li>
      <li id="galleryDisplayTab" class="uk-height-1-1 uk-width-1-1">
        <galleryDisplay />
      </li>
    </ul>
  </div>
</template>

<script>
// Import basic UIkit
import UIkit from "uikit";

// Import components
import connectDisplay from "./viewComponents/connectDisplay.vue";
import streamDisplay from "./viewComponents/streamDisplay.vue";
import galleryDisplay from "./viewComponents/galleryDisplay.vue";

// Export main app
export default {
  name: "PanelRight",

  components: {
    connectDisplay,
    streamDisplay,
    galleryDisplay
  },

  mounted() {
    // Attach methods to UIkit events for tab switching
    var context = this;

    // Stream tab leave
    UIkit.util.on("#streamDisplayTab", "hidden", function() {
      console.log("Stream tab hidden");
      if (context.$store.state.globalSettings.trackWindow == true) {
        context.$root.$emit("globalTogglePreview", false);
      }
    });

    // Stream tab enter
    UIkit.util.on("#streamDisplayTab", "shown", function() {
      console.log("Stream tab entered");
      UIkit.update();
      if (context.$store.state.globalSettings.trackWindow == true) {
        context.$root.$emit("globalTogglePreview", true);
      }
    });

    // Gallery tab enter
    UIkit.util.on("#galleryDisplayTab", "shown", function() {
      console.log("Gallery tab entered");
      UIkit.update();
      context.$root.$emit("globalUpdateCaptureList");
    });

    // Create a global event to switch the active tab
    var switcherObj = UIkit.tab("#tabContainer");
    console.log(switcherObj);
    this.$root.$on("globalTogglePanelRightTab", state => {
      console.log(`Toggling panelRight tab to ${state}`);
      switcherObj.show(1);
    });
  },

  methods: {}
};
</script>

<style scoped lang="less">
.uk-tab {
  padding-left: 0;
}
</style>

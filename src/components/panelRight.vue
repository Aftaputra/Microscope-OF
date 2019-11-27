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
      <!-- Connect tab button -->
      <li :class="[{ 'uk-active': selectedTab == 0 }]">
        <a href="#" uk-switcher-item="connect" @click="selectedTab = 0"
          >Connect</a
        >
      </li>
      <!-- Preview tab button -->
      <li
        :class="[
          { 'uk-disabled': !$store.getters.ready },
          { 'uk-active': selectedTab == 1 }
        ]"
      >
        <a href="#" uk-switcher-item="preview" @click="selectedTab = 1">Live</a>
      </li>
      <!-- Gallery tab button -->
      <li
        :class="[
          { 'uk-disabled': !$store.getters.ready },
          { 'uk-active': selectedTab == 2 }
        ]"
      >
        <a href="#" uk-switcher-item="gallery" @click="selectedTab = 2"
          >Gallery</a
        >
      </li>
    </ul>
    <ul class="uk-flex uk-flex-1 uk-overflow-auto uk-margin-remove">
      <!-- Connect tab -->
      <div
        v-show="selectedTab == 0"
        id="connectDisplayTab"
        class="uk-height-1-1 uk-width-1-1"
      >
        <connectDisplay />
      </div>
      <!-- Preview tab -->
      <div
        v-if="$store.getters.ready"
        v-show="selectedTab == 1"
        id="streamDisplayTab"
        class="uk-height-1-1 uk-width-1-1"
      >
        <streamDisplay />
      </div>
      <!-- Gallery tab -->
      <div
        v-if="$store.getters.ready"
        v-show="selectedTab == 2"
        id="galleryDisplayTab"
        class="uk-height-1-1 uk-width-1-1"
      >
        <galleryDisplay />
      </div>
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

  data: function() {
    return {
      selectedTab: 0,
      unwatchStoreFunction: null
    };
  },

  watch: {
    selectedTab: function(index) {
      // If entering the gallery
      if (index == 2) {
        console.log("Gallery tab entered");
        this.$root.$emit("globalUpdateCaptureList");
      }
      // If entering the stream
      if (index == 1) {
        console.log("Stream tab entered");
        this.$root.$emit("globalTogglePreview", true);
      }
      // If leaving the stream
      else {
        console.log("Stream tab hidden");
        this.$root.$emit("globalTogglePreview", false);
      }
    }
  },

  created: function() {
    // Watch for host 'ready', then update status
    this.unwatchStoreFunction = this.$store.watch(
      (state, getters) => {
        return getters.ready;
      },
      ready => {
        if (ready) {
          console.log("Right panel now ready");
          this.selectedTab = 1;
        } else {
          console.log("Right panel now disabled");
          this.selectedTab = 0;
        }
      }
    );
  },

  beforeDestroy() {
    // Then we call that function here to unwatch
    if (this.unwatchStoreFunction) {
      this.unwatchStoreFunction();
      this.unwatchStoreFunction = null;
    }
  },

  methods: {
    switchTab: function(index) {
      var switcherObj = UIkit.switcher("#tabContainer");
      console.log(switcherObj);
      console.log(switcherObj.toggles);
      console.log(`Switching to ${index}`);
      var a = switcherObj.show(index);
      console.log(a);
    }
  }
};
</script>

<style scoped lang="less">
.uk-tab {
  padding-left: 0;
}
</style>

<template>
  <div id="scan-modal" ref="scanModal" style="padding: 10px;" uk-modal>
    <div
      class="uk-modal-dialog uk-modal-body"
      v-if="selectedScan"
      style="padding: 10px; width: 95%; height: 95%; display: flex; flex-direction: column;"
    >
      <h2 class="uk-modal-title" style="flex: 0 0 auto;">
        {{ selectedScan.name }}
        <button class="uk-modal-close uk-float-right" type="button">
          <span class="material-symbols-outlined">close</span>
        </button>
        <button class="uk-float-right" type="button" @click="goFullscreen">
          <span class="material-symbols-outlined">fullscreen</span>
        </button>
      </h2>

      <!-- Viewer -->
      <div
        v-if="selectedScanDZI"
        id="viewer_container"
        class="viewer_container"
      >
        <OpenSeadragonViewer
          id="openseadragon"
          ref="openseadragon"
          :src="selectedScanDZI"
        />
      </div>

      <!-- Controls -->
      <div
        v-if="selectedScanDZI"
        class="viewer-controls"
      >
        <div class="controlsContainer">
          <label>
            Brightness
            <input
              type="range"
              min="0.2"
              max="1.8"
              step="0.01"
              v-model.number="brightness"
              @input="updateViewerFilter"
            />
          </label>
          <label>
            Contrast
            <input
              type="range"
              min="0.2"
              max="1.8"
              step="0.01"
              v-model.number="contrast"
              @input="updateViewerFilter"
            />
          </label>
          <label>
            Saturation
            <input
              type="range"
              min="0"
              max="2"
              step="0.01"
              v-model.number="saturation"
              @input="updateViewerFilter"
            />
          </label>
        </div>

        <button
          type="button"
          class="uk-button uk-button-default"
          style="margin-top: 0.5rem;"
          @click="resetFilters"
        >
          Reset Filters
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import UIkit from "uikit";
import OpenSeadragonViewer from "./openSeadragonViewer.vue";

export default {
  name: "ScanViewerModal",
  components: { OpenSeadragonViewer },
  props: {
    selectedScan: {
      type: Object,
      default: null,
    },
    baseUri: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      brightness: 1,
      contrast: 1,
      saturation: 1,
    };
  },
  computed: {
    selectedScanDZI() {
      if (this.selectedScan && this.selectedScan.dzi) {
        return `${this.baseUri}/scans/${this.selectedScan.name}/images/${this.selectedScan.dzi}`;
      }
      return null;
    },
  },
  methods: {
    show() {
      UIkit.modal(this.$refs.scanModal).show();
    },
    hide() {
      UIkit.modal(this.$refs.scanModal).hide();
    },
    goFullscreen() {
      this.$refs.openseadragon.openFullscreen();
    },
    updateViewerFilter() {
      const viewer = this.$refs.openseadragon;
      if (viewer) {
        viewer.brightness = this.brightness;
        viewer.contrast = this.contrast;
        viewer.saturation = this.saturation;
        viewer.updateFilter();
      }
    },
    resetFilters() {
      this.brightness = 1;
      this.contrast = 1;
      this.saturation = 1;
      this.updateViewerFilter();
    },
  },
};
</script>

<style scoped>
input[type="range"] {
  pointer-events: auto;
  z-index: 1001;
}

.controlsContainer {
    display: flex;
    justify-content: center;
    gap: 1.5rem;
}

.viewer-controls {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
}

.viewer_container {
    flex: 1 1 auto;
    position: relative;
    overflow: hidden;
}
</style>

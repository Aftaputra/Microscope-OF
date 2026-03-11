<template>
  <div id="scan-modal" ref="scanModal" uk-modal>
    <div v-if="selectedScan" id="scan-modal-body" class="uk-modal-dialog uk-modal-body">
      <h2 id="scan-modal-title" class="uk-modal-title">
        {{ selectedScan.name }}
        <button class="uk-modal-close uk-float-right" type="button">
          <span class="material-symbols-outlined">close</span>
        </button>
        <button class="uk-float-right" type="button" @click="goFullscreen">
          <span class="material-symbols-outlined">fullscreen</span>
        </button>
      </h2>

      <!-- Viewer -->
      <div v-if="selectedScanDZI" id="viewer_container" class="viewer_container">
        <OpenSeadragonViewer
          id="openseadragon"
          ref="openseadragon"
          :src="selectedScanDZI"
          :brightness="brightness"
          :contrast="contrast"
          :saturation="saturation"
          @entering-fullscreen="enteringFullscreen = true"
        />
      </div>

      <!-- Controls -->
      <div v-if="selectedScanDZI" class="viewer-controls">
        <div class="controlsContainer">
          <label>
            Brightness
            <input v-model.number="brightness" type="range" min="0.2" max="1.8" step="0.01" />
          </label>
          <label>
            Contrast
            <input v-model.number="contrast" type="range" min="0.2" max="1.8" step="0.01" />
          </label>
          <label>
            Saturation
            <input v-model.number="saturation" type="range" min="0" max="2" step="0.01" />
          </label>
        </div>

        <button
          type="button"
          class="uk-button uk-button-default reset-button"
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
  components: {
    OpenSeadragonViewer,
  },
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
      enteringFullscreen: false,
      modalEl: null,
      beforeHideHandler: null,
    };
  },
  computed: {
    selectedScanDZI() {
      if (this.selectedScan && this.selectedScan.dzi) {
        return `${this.baseUri}/data/smart_scan/${this.selectedScan.name}/images/${this.selectedScan.dzi}`;
      }
      return null;
    },
  },
  mounted() {
    this.modalEl = this.$refs.scanModal;
    this.beforeHideHandler = (event) => {
      if (this.enteringFullscreen) {
        event.preventDefault();
        this.enteringFullscreen = false;
      }
    };
    this.modalEl.addEventListener("beforehide", this.beforeHideHandler);
  },
  beforeUnmount() {
    if (this.modalEl && this.beforeHideHandler) {
      this.modalEl.removeEventListener("beforehide", this.beforeHideHandler);
    }
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
    resetFilters() {
      this.brightness = 1;
      this.contrast = 1;
      this.saturation = 1;
    },
  },
};
</script>

<style scoped>
input[type="range"] {
  pointer-events: auto;
  z-index: 1001;
}

#scan-modal {
  padding: 10px;
}

#scan-modal-body {
  padding: 10px;
  width: 95%;
  height: 95%;
  display: flex;
  flex-direction: column;
}

#scan-modal-title {
  flex: 0 0 auto;
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

.reset-button {
  margin-top: 0.5rem;
}
</style>

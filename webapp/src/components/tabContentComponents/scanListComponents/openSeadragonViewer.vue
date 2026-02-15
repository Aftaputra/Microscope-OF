<template>
  <div ref="osdViewerContainer" class="osd-viewer-container uk-height-1-1">
    <div id="openseadragon" ref="osdContainer"></div>
  </div>
</template>

<script>
import OpenSeaDragon from "openseadragon";
// vue3 migration
import { useIntersectionObserver } from "@vueuse/core";

export default {
  name: "OpenSeadragonViewer",

  props: {
    src: {
      type: String,
      required: true,
    },
    brightness: {
      type: Number,
      required: true,
    },
    contrast: {
      type: Number,
      required: true,
    },
    saturation: {
      type: Number,
      required: true,
    },
  },

  data: function () {
    return {
      osdViewer: null,
    };
  },

  watch: {
    src: {
      immediate: true,
      handler(newVal) {
        this.loadOpenSeaDragon(newVal);
      },
    },
    brightness() {
      this.updateFilter();
    },
    contrast() {
      this.updateFilter();
    },
    saturation() {
      this.updateFilter();
    },
  },

  async mounted() {
    useIntersectionObserver(
      this.$refs.osdViewerContainer,
      ([{ isIntersecting }]) => {
        this.visibilityChanged(isIntersecting);
      },
      { threshold: 0.0 },
    );

    if (this.src) {
      this.loadOpenSeaDragon(this.src);
    }
  },

  beforeUnmount() {
    // Remove global signal listener to perform a gallery refresh
    if (this.osdViewer) {
      this.osdViewer.destroy();
    }
  },

  methods: {
    visibilityChanged(isVisible) {
      // adding this check to avoid error when the viewer is not yet initialized.
      if (isVisible) {
        if (!this.osdViewer && this.src) {
          this.loadOpenSeaDragon(this.src);
        }
      } else {
        if (this.osdViewer) {
          this.osdViewer.destroy();
          this.osdViewer = null;
        }
      }
    },

    async loadOpenSeaDragon() {
      if (this.osdViewer) {
        this.osdViewer.destroy();
      }
      await this.$nextTick();
      this.osdViewer = OpenSeaDragon({
        element: this.$refs.osdContainer,
        crossOriginPolicy: "Anonymous",
        tileSources: this.src,
        showNavigationControl: false,
        maxZoomPixelRatio: 2,
        gestureSettingsMouse: {
          clickToZoom: false,
        },
      });

      this.updateFilter();
    },

    updateFilter() {
      const viewerEl = document.getElementById("openseadragon");
      if (viewerEl) {
        viewerEl.style.filter = `
          brightness(${this.brightness})
          contrast(${this.contrast})
          saturate(${this.saturation})
        `;
      }
    },
    openFullscreen() {
      if (this.osdViewer) {
        this.osdViewer.setFullScreen(true);
      }
    },
  },
};
</script>

<style lang="less" scoped>
#openseadragon {
  width: 100%;
  height: 100%;
  background-color: black;
  z-index: 1;
}
</style>

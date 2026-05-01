<template>
  <div
    id="stream-display"
    ref="streamDisplay"
    class="stream-display uk-width-1-1 uk-height-1-1 scrollTarget"
  >
    <img
      v-if="isVisible"
      ref="click-frame"
      class="uk-align-center uk-margin-remove-bottom"
      :src="streamImgUri"
      alt="Stream"
    />
  </div>
</template>

<script>
import { useIntersectionObserver } from "@vueuse/core";
import { useSettingsStore } from "@/stores/settings.js";
import { mapState } from "pinia";

// Export main app
export default {
  name: "MiniStreamDisplay",

  data: function () {
    return {
      isVisible: false,
    };
  },

  computed: {
    ...mapState(useSettingsStore, ["baseUri"]),
    streamImgUri() {
      return `${this.baseUri}/camera/mjpeg_stream`;
    },
  },

  mounted() {
    useIntersectionObserver(
      this.$refs.streamDisplay,
      ([{ isIntersecting }]) => {
        this.isVisible = isIntersecting;
      },
      {
        threshold: 0.0,
      },
    );
  },
};
</script>

<style scoped lang="less">
.stream-display img {
  text-align: center;
  object-fit: contain;
  border: 1px solid #555;
}

.stream-display {
  width: 100%;
  height: 100%;
}

.position-relative {
  position: relative !important;
}

.text-center {
  text-align: center;
}
</style>

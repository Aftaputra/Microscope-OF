<template>
  <div
    id="stream-display"
    ref="streamDisplay"
    class="stream-display uk-width-1-1 uk-height-1-1 scrollTarget"
  >
    <img
      ref="click-frame"
      class="uk-align-center uk-margin-remove-bottom"
      :hidden="!streamEnabled"
      :src="streamImgUri"
      alt="Stream"
    />

    <div v-if="!streamEnabled" class="uk-height-1-1">
      <div v-if="$store.state.waiting" class="uk-position-center">
        <div uk-spinner="ratio: 4.5"></div>
      </div>

      <div v-else class="uk-position-center position-relative text-center">
        No active connection
      </div>
    </div>
  </div>
</template>

<script>
// Export main app
export default {
  name: "MiniStreamDisplay",

  data: function() {
    return {};
  },

  computed: {
    streamEnabled: function() {
      return (
        this.$store.getters.ready &&
        !this.$store.state.globalSettings.disableStream
      );
    },
    streamImgUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/streams/mjpeg`;
    }
  },
  methods: {}
};
</script>

<style scoped lang="less">
.stream-display img {
  text-align: center;
  object-fit: contain;
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

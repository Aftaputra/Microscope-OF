<template>
  <div class="connectDisplayLite uk-padding uk-padding-remove-left">
    Lite connect
  </div>
</template>

<script>
// Export main app
export default {
  name: "ConnectDisplayLite",

  components: {},

  data: function() {
    return {};
  },

  mounted() {
    // Connect to the current location
    // NOTE: This assumes that the GUI is being served from the same location as the API"
    this.connectToHost(location);
  },

  methods: {
    connectToHost: function(host) {
      console.log(host);

      // Commit the hostname and port to store
      this.$store.commit("resetState");
      this.$store.commit("changeHost", [host.hostname, host.port]);
      this.$store.commit("setConnected");
    }
  }
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="less">
.connect-card-align-top {
  margin-top: 52px;
}
</style>

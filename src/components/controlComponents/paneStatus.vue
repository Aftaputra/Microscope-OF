<template>
  <div class="host-input">
    <div v-if="$store.getters.ready">
      <div v-if="$store.state.apiConfig.name">
        <b>Device name:</b> <br />
        {{ $store.state.apiConfig.name }}
      </div>
      <hr />
      <div class="uk-margin-small-bottom">
        <b>Host:</b>
        <br />
        {{ $store.state.host }}
      </div>
      <div>
        <b>Server version:</b> <br />
        {{ $store.state.apiState.version }}
      </div>
      <hr />
      <div class="uk-margin-small-bottom">
        <b>Camera:</b>
        <br />
        <div v-if="$store.state.apiState.camera.board">
          {{ $store.state.apiState.camera.board }}
        </div>
        <div v-else class="uk-text-danger"><b>No camera connected</b></div>
      </div>
      <div>
        <b>Stage:</b>
        <br />
        <div v-if="$store.state.apiState.stage.board">
          {{ $store.state.apiState.stage.board }}
        </div>
        <div v-else class="uk-text-danger"><b>No stage connected</b></div>
      </div>
    </div>
    <div v-else-if="$store.state.waiting">
      <progressBar></progressBar>
    </div>
    <div v-else-if="$store.state.error">
      <b>Error:</b> {{ $store.state.error }}
    </div>
    <div v-else>No active connection</div>
  </div>
</template>

<script>
import progressBar from "../genericComponents/progressBar";

export default {
  name: "PaneStatus",

  components: {
    progressBar
  },

  data: function() {
    return {};
  },

  computed: {},

  watch: {},

  mounted() {},

  methods: {}
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="less"></style>

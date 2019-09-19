<template>
<div class="host-input">

  <div v-if="$store.getters.ready">
    <p><b>Host:</b> {{ $store.state.host }}</p>
    <p><b>Base URI:</b> {{ $store.getters.uri }}</p>
    <p v-if="$store.state.apiConfig.name"><b>Device name:</b> {{ $store.state.apiConfig.name }}</p>
  </div>
  <div v-else-if="$store.state.waiting"><div uk-spinner></div></div>
  <div v-else-if="$store.state.error"><b>Error:</b> {{ $store.state.error }}</div>
  <div v-else>No active connection</div>

</div>
</template>

<script>

export default {
  name: 'paneStatus',

  data: function () {
    return {
    }  
  },

  mounted() {
  },

  // When savedHosts changes, serialise to JSON and save to localStorage
  watch: {
  },

  methods: {
  },

  computed: {
  }

}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="less">
</style>

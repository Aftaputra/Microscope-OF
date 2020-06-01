<template>
  <div class="uk-flex uk-flex-column uk-flex-center uk-height-1-1">
    <div
      v-if="$store.state.waiting"
      class="uk-align-center"
      uk-spinner="ratio: 3"
    ></div>
    <div v-if="$store.state.waiting" class="uk-align-center">Loading...</div>
    <i class="material-icons uk-align-center error-icon">error_outline</i>
    <div v-if="$store.state.error" class="uk-align-center">
      {{ $store.state.error }}
    </div>
  </div>
</template>

<script>
// Export main app
export default {
  name: "LoadingContent",

  components: {},

  data: function() {
    return {};
  }
};
</script>

<style scoped lang="less">
.error-icon {
  font-size: 120px;
}
</style>

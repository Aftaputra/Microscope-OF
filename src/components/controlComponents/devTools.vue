<template>
  <div>
    <form class="uk-form-stacked" @submit.prevent="overrideAPIHost">
      <label class="uk-form-label">API origin</label>
      <input class="uk-input" type="text" v-model="currentOrigin" />
    </form>
  </div>
</template>

<script>
// Export main app
export default {
  name: "DevTools",

  components: {},

  data: function() {
    return {
      currentOrigin: this.$store.state.origin
    };
  },

  methods: {
    overrideAPIHost: function() {
      this.$store.commit("changeOrigin", this.currentOrigin);
    }
  }
};
</script>

<style scoped lang="less">
.error-icon {
  font-size: 120px;
}
</style>

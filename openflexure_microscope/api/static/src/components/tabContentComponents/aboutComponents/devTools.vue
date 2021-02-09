<template>
  <div>
    <form class="uk-form-stacked" @submit.prevent="overrideAPIHost">
      <label class="uk-form-label">Override API origin</label>
      <input v-model="newOrigin" class="uk-input" type="text" />
      <button class="uk-button uk-button-default uk-margin-small">
        Apply
      </button>
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
      newOrigin: this.$store.state.origin
    };
  },

  mounted() {
    if (localStorage.overrideOrigin){
      this.newOrigin = localStorage.overrideOrigin;
    }else{
      this.newOrigin = "http://microscope.local:5000";
    }
  },

  methods: {
    overrideAPIHost: function() {
      this.$store.commit("changeOrigin", this.newOrigin);
      localStorage.overrideOrigin = this.newOrigin
    }
  }
};
</script>

<style scoped lang="less">
.error-icon {
  font-size: 120px;
}
</style>

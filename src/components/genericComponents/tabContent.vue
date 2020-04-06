<template>
  <div
    v-if="!(requireConnection && !$store.getters.ready)"
    :hidden="currentTab != tabID"
    class="uk-width-expand uk-height-1-1"
  >
    <div class="section-content"><slot></slot></div>
  </div>
</template>

<script>
export default {
  name: "TabContent",

  props: {
    tabID: {
      type: String,
      required: true
    },
    currentTab: {
      type: String,
      required: true
    },
    requireConnection: Boolean
  },
  computed: {},

  methods: {}
};
</script>

<style lang="less" scoped>
.section-heading {
  display: block;
  font-size: 12px;
  text-transform: uppercase;
  line-height: 20px;
  cursor: default;
}

.section-content {
  padding: 0;
  height: 100%;
}
</style>

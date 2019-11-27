<template>
  <div
    v-if="!(requireConnection && !$store.getters.ready)"
    :hidden="currentTab != id"
    class="uk-width-expand"
  >
    <div class="section-heading">{{ id }}</div>
    <div class="section-content"><slot></slot></div>
  </div>
</template>

<script>
export default {
  name: "TabContent",

  props: {
    id: {
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

.section-content,
.section-heading {
  padding: 9px 10px;
}
</style>

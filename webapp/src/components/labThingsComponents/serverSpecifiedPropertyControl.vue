<template>
  <property-control
    :thing="propertyData.thing"
    :property-name="propertyData.property_name"
    :thing-name="propertyData.thing"
    :label="propertyData.label"
    :read-back="propertyData.read_back"
    :read-back-delay="propertyData.read_back_delay"
  />
</template>

<script>
import PropertyControl from "./propertyControl.vue";
// vue3 migration
import { markRaw } from "vue";

// Export main app
export default {
  name: "ServerSpecifiedPropertyControl",

  components: {
    PropertyControl: markRaw(PropertyControl),
  },

  props: {
    propertyData: {
      type: Object,
      required: true,
    },
  },
};
</script>

<style lang="less"></style>

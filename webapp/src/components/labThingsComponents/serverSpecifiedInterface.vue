<template>
  <div v-for="(element, index) in elements" :key="index" class="uk-margin">
    <!-- eslint-disable vue/no-v-html -->
    <div v-if="element.element_type === 'html_block'" v-html="element.html"></div>
    <!-- eslint-enable -->
    <server-specified-property-control
      v-else-if="element.element_type === 'property_control'"
      :property-data="element"
    />
    <server-specified-action-button
      v-else-if="element.element_type === 'action_button'"
      :property-data="element"
    />
    <simple-accordion v-else-if="element.element_type === 'accordion'" :title="element.title">
      <server-specified-interface :elements="element.children" />
    </simple-accordion>
    <div v-else-if="element.element_type === 'container'" :class="element.css_class">
      <server-specified-interface :elements="element.children" />
    </div>
  </div>
</template>

<script>
import SimpleAccordion from "../genericComponents/simpleAccordion.vue";
import ServerSpecifiedPropertyControl from "./serverSpecifiedPropertyControl.vue";
import ServerSpecifiedActionButton from "./serverSpecifiedActionButton.vue";

// Export main app
export default {
  name: "ServerSpecifiedInterface",

  components: {
    SimpleAccordion,
    ServerSpecifiedPropertyControl,
    ServerSpecifiedActionButton,
  },

  props: {
    elements: {
      type: Array,
      required: true,
    },
  },
};
</script>

<style lang="less"></style>

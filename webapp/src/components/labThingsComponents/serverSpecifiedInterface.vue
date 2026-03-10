<template>
  <div v-for="(element, index) in elements" :key="index" class="uk-margin">
    <!-- eslint-disable vue/no-v-html -->
    <component :is="'h' + element.level" v-if="element.element_type === 'header_block'">
      <span v-html="element.text"></span>
    </component>
    <p v-if="element.element_type === 'text_block'" v-html="element.text"></p>
    <ul v-if="element.element_type === 'bullet_block'">
      <li
        v-for="(bulletText, bulletIndex) in element.bullets"
        :key="'bullet-' + bulletIndex"
        v-html="bulletText"
      ></li>
    </ul>
    <!-- eslint-enable -->
    <server-specified-property-control
      v-else-if="element.element_type === 'property_control'"
      :property-data="element"
    />
    <server-specified-action-button
      v-else-if="element.element_type === 'action_button'"
      :action-data="element"
      @request-update="$emit('requestUpdate')"
    />
    <simple-accordion v-else-if="element.element_type === 'accordion'" :title="element.title">
      <server-specified-interface
        :elements="element.children"
        @request-update="$emit('requestUpdate')"
      />
    </simple-accordion>
    <div v-else-if="element.element_type === 'container'" :class="element.css_class">
      <server-specified-interface
        :elements="element.children"
        @request-update="$emit('requestUpdate')"
      />
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

  emits: ["requestUpdate"],
};
</script>

<style lang="less"></style>

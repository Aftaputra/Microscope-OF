<template>
  <!-- Grid managing tab content -->
  <div uk-grid class="uk-height-1-1 uk-margin-remove uk-padding-remove">
    <div class="control-component">
      <JsonForm v-bind="$props" v-on="$listeners" />
    </div>
    <div class="view-component uk-width-expand">
      <galleryDisplay v-if="viewPanel == 'gallery'" />
      <settingsDisplay v-else-if="viewPanel == 'settings'" />
      <streamDisplay v-else />
    </div>
  </div>
</template>

<script>
import JsonForm from "../pluginComponents/JsonForm";
import streamDisplay from "../viewComponents/streamDisplay.vue";
import galleryDisplay from "../viewComponents/galleryDisplay.vue";
import settingsDisplay from "../viewComponents/settingsDisplay.vue";

export default {
  name: "ExtensionContent",

  components: {
    JsonForm,
    streamDisplay,
    galleryDisplay,
    settingsDisplay
  },

  props: {
    name: {
      type: String,
      required: false,
      default: "Plugin"
    },
    schema: {
      type: Array,
      required: true
    },
    route: {
      type: String,
      required: true
    },
    isTask: {
      type: Boolean,
      required: false,
      default: false
    },
    submitLabel: {
      type: String,
      required: false,
      default: "Submit"
    },
    emitOnResponse: {
      type: String,
      required: false,
      default: null
    },
    viewPanel: {
      type: String,
      required: false,
      default: "stream"
    }
  }
};
</script>

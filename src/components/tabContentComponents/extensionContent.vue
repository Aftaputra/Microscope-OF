<template>
  <!-- Grid managing tab content -->
  <div uk-grid class="uk-height-1-1 uk-margin-remove uk-padding-remove">
    <div class="control-component">
      <JsonForm v-bind="$props" v-on="$listeners" />
    </div>
    <div class="view-component uk-width-expand"></div>
  </div>
</template>

<script>
import JsonForm from "../pluginComponents/JsonForm";

export default {
  name: "ExtensionContent",

  components: {
    JsonForm
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
    }
  }
};
</script>

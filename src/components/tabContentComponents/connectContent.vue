<template>
  <!-- Grid managing tab content -->
  <div uk-grid class="uk-height-1-1 uk-margin-remove uk-padding-remove">
    <div class="view-component uk-width-expand">
      <connectDisplayLite v-if="liteMode" />
      <connectDisplay v-else />
    </div>
  </div>
</template>

<script>
import connectDisplay from "../viewComponents/connectDisplay.vue";

export default {
  name: "ConnectContent",

  components: {
    connectDisplay
  },

  data: function() {
    return {
      liteMode: process.env.VUE_APP_LITEMODE == "true" ? true : false
    };
  }
};
</script>

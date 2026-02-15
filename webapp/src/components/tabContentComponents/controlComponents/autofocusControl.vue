<template>
  <div>
    <p>Autofocus</p>
    <div class="uk-margin">
      <action-button
        thing="autofocus"
        action="fast_autofocus"
        :submit-data="{ dz: 2000 }"
        :submit-label="'Autofocus'"
        :button-primary="true"
        :submit-on-event="'globalFastAutofocusEvent'"
        @task-started="onAutofocus"
        @finished="afterAutofocus"
        @error="modalError"
      />
    </div>
  </div>
</template>
<script>
import ActionButton from "../../labThingsComponents/actionButton.vue";
import { eventBus } from "../../../eventBus.js";

export default {
  name: "AutofocusControl",

  components: {
    ActionButton,
  },

  data: function () {
    return {
      isAutofocusing: false,
    };
  },

  methods: {
    onAutofocus() {
      this.isAutofocusing = true;
    },
    afterAutofocus() {
      this.isAutofocusing = false;
      eventBus.emit("globalUpdatePositionEvent");
    },
  },
};
</script>

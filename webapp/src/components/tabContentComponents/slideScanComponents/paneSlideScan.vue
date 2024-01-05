<template>
  <div class="uk-padding-small">
    <div v-show="!backendOK" class="uk-alert-danger">
      No scan back-end found.
    </div>
    <div v-show="backendOK">
      <taskSubmitter
        :submit-url="smartScanUri"
        submit-label="Start tiled scan"
        :can-terminate="true"
        :modal-progress="true"
      />
    </div>
  </div>
</template>

<script>
import taskSubmitter from "../../genericComponents/taskSubmitter";

export default {
  components: {
    taskSubmitter
  },

  computed: {
    backendOK() {
      return this.thingAvailable("smart_scan");
    },
    smartScanUri() {
      return this.thingActionUrl("smart_scan", "sample_scan");
    }
  },

  methods: {
    onScanError: function(error) {
      this.scanRunning = false;
      this.modalError(error);
    }
  }
};
</script>

<template>
  <div v-if="!backendOK" class="uk-alert-danger">
    No scan back-end found.
  </div>
  <!-- Grid managing tab content -->
  <div v-else uk-grid class="uk-height-1-1 uk-margin-remove uk-padding-remove">
    <div class="control-component uk-padding-small">
      <div v-show="!scanning">
        <ul uk-accordion="multiple: true">
          <li>
            <a class="uk-accordion-title" href="#">Configure</a>
            <div class="uk-accordion-content">
              <div class="uk-margin">
                <propertyControl
                  thing-name="smart_scan"
                  property-name="max_range"
                  label="Maximum Distance (steps)"
                />
                <div class="uk-margin">
                  <propertyControl
                    thing-name="smart_scan"
                    property-name="autofocus_dz"
                    label="Autofocus range (steps)"
                  />
                </div>
                <div class="uk-margin">
                  <propertyControl
                    thing-name="smart_scan"
                    property-name="overlap"
                    label="Image overlap (0-1)"
                  />
                </div>
              </div>
            </div>
          </li>
        </ul>
        <div class="uk-margin">
          <taskSubmitter
            :submit-url="smartScanUri"
            submit-label="Start smart scan"
            :can-terminate="true"
            :modal-progress="true"
            :submit-data="{ sample_check: false }"
            @update:taskRunning="scanning = $event"
            @update:taskStatus="taskStatus = $event"
            @update:progress="progress = $event"
            @update:log="log = $event"
          />
        </div>
        <div class="uk-margin">
          <taskSubmitter
            :submit-url="smartScanUri"
            submit-label="Start manual scan"
            :can-terminate="true"
            :modal-progress="true"
            :submit-data="{ sample_check: false }"
            @update:taskRunning="scanning = $event"
            @update:taskStatus="taskStatus = $event"
            @update:progress="progress = $event"
            @update:log="log = $event"
          />
        </div>
      </div>
    </div>
    <div class="view-component uk-width-expand">
      <streamDisplay />
    </div>
  </div>
</template>

<script>
import streamDisplay from "./streamContent.vue";
import taskSubmitter from "../genericComponents/taskSubmitter";
import propertyControl from "../labThingsComponents/propertyControl.vue";

export default {
  name: "SlideScanContent",

  components: {
    streamDisplay,
    taskSubmitter,
    propertyControl
  },

  data() {
    return {
      lastScanName: null,
      scanning: false,
      taskStatus: null,
      progress: null,
      log: []
    };
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

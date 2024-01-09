<template>
  <div class="uk-padding-small">
    <div v-show="!backendOK" class="uk-alert-danger">
      No scan back-end found.
    </div>
    <div v-show="backendOK">
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
          :submit-data="{ sample_check: true }"
          submit-label="Start smart scan"
          :can-terminate="true"
          :modal-progress="true"
          />
        </div>
        <div class="uk-margin">
          <taskSubmitter
          :submit-url="smartScanUri"
          :submit-data="{ sample_check: false }"
          submit-label="Start manual scan"
          :can-terminate="true"
          :modal-progress="true"
          />
        </div>
    </div>
  </div>
</template>

<script>
import taskSubmitter from "../../genericComponents/taskSubmitter";
import propertyControl from "../../labThingsComponents/propertyControl.vue";

export default {
  components: {
    taskSubmitter,
    propertyControl
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

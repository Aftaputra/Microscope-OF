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
              </div>
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
                <div class="uk-margin">
                <propertyControl
                  thing-name="smart_scan"
                  property-name="stitch_tiff"
                  label="When stitching, produce a pyramidal tiff"
                />
              </div>
            </div>
          </li>
          <li class="uk-open">
            <a class="uk-accordion-title" href="#">Scan Settings</a>
            <div class="uk-accordion-content">
              <div class="uk-margin">
                <propertyControl
                  thing-name="smart_scan"
                  property-name="skip_background"
                  label="Detect and skip empty fields"
                />
              </div>
              <div class="uk-margin">
                <propertyControl
                  thing-name="smart_scan"
                  property-name="stitch_automatically"
                  label="Automatically stitch images together"
                />
              </div>
            </div>
          </li>
        </ul>
        <label class="uk-form-label" for="form-stacked-text">Sample ID</label>
        <div class="uk-form-controls">
          <input
            v-model="scan_name"
            class="uk-input uk-form-small"
            type="text"
            name="Scan Name"
          />
        </div>
        <div class="uk-margin">
          <taskSubmitter
            ref="smartScanTaskSubmitter"
            :submit-url="smartScanUri"
            :submit-data="{ scan_name: scan_name }"
            submit-label="Start smart scan"
            :can-terminate="true"
            @taskStarted="startScanning"
            @update:taskStatus="taskStatus = $event"
            @update:progress="progress = $event"
            @update:log="log = $event"
          />
        </div>
      </div>
      <div v-show="scanning">
      <h2 v-if="displayImageOnRight">
        Live stitching preview
      </h2>
        <mini-stream-display v-if="displayImageOnRight" />
        <action-log-display
          id="log-display"
          :log="log"
          :task-status="taskStatus"
        />
        <action-progress-bar :progress="progress" :task-status="taskStatus" />
        <button
          v-if="cancellable"
          type="button"
          class="uk-button uk-button-danger uk-margin-remove uk-float-right uk-width-1-1"
          @click="$refs.smartScanTaskSubmitter.terminateTask()"
        >
          Cancel
        </button>
        <button
          v-if="!cancellable"
          type="button"
          class="uk-button uk-button-danger uk-margin-remove uk-float-right uk-width-1-1"
          @click="scanning = false; lastStitchedImage=null;"
        >
          Close
        </button>
      </div>
      <h3 v-if="scanning">
        Scan ID: {{ scan_name }}
      </h3>
    </div>
    <div class="view-image uk-width-expand uk-height-1-1">
      <img v-if="displayImageOnRight" class=image-fit :src="lastStitchedImage" id="last-stitched-image">
      <streamDisplay v-else />
    </div>
  </div>
</template>

<script>
import streamDisplay from "./streamContent.vue";
import taskSubmitter from "../genericComponents/taskSubmitter";
import propertyControl from "../labThingsComponents/propertyControl.vue";
import actionLogDisplay from "../genericComponents/actionLogDisplay.vue";
import actionProgressBar from "../genericComponents/actionProgressBar.vue";
import MiniStreamDisplay from '../genericComponents/miniStreamDisplay.vue';

export default {
  name: "SlideScanContent",

  components: {
    streamDisplay,
    taskSubmitter,
    propertyControl,
    actionLogDisplay,
    actionProgressBar,
    MiniStreamDisplay
  },

  data() {
    return {
      lastScanName: null,
      scanning: false,
      taskStatus: "pending",
      correlateStatus: "",
      stitchFromStageStatus: "",
      progress: null,
      log: [],
      lastStitchedImage: null,
      scan_name: ""
    };
  },

  computed: {
    backendOK() {
      return this.thingAvailable("smart_scan");
    },
    smartScanUri() {
      return this.thingActionUrl("smart_scan", "sample_scan");
    },
    cancellable() {
      return (this.taskStatus == "running") | (this.taskStatus == "pending");
    },
    displayImageOnRight() {
      return this.scanning & this.lastStitchedImage !== null;
    }
  },

  methods: {
    onScanError: function(error) {
      this.scanRunning = false;
      this.modalError(error);
    },
    correlateCurrentScan() {

    },
    startScanning() {
      this.lastStitchedImage = null;
      this.scanning = true;
      setTimeout(this.pollScan, 1000);
    },
    async pollScan() {
      if (this.cancellable) {  // while the scan is running
        let mtime = await this.readThingProperty("smart_scan", "latest_preview_stitch_time");
        if (mtime !== null) {
          this.lastStitchedImage = `${this.$store.getters.baseUri}/smart_scan/latest_preview_stitch.jpg?t=${mtime}`;
        }
        setTimeout(this.pollScan, 1000);  // keep rescheduling until it's stopped
      }
    }
  }
};
</script>

<style scoped>
#log-display {
  height: 20em;
}
.control-component {
  width: 33%;
}
</style>

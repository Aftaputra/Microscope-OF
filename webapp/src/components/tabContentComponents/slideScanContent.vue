<template>
  <div uk-grid class="uk-height-1-1 uk-margin-remove uk-padding-remove">
    <div class="control-component uk-padding-small">
      <div v-show="!scanning" ref="slideScanView" class="uk-padding-small">
        <!-- Workflow Selection Dropdown -->
        <div class="uk-margin">
          <label class="uk-form-label">Workflow</label>

          <select
            class="uk-select uk-form-small"
            :value="workflowName"
            @change="setWorkflow($event.target.value)"
          >
            <option v-for="(label, name) in workflowOptions" :key="name" :value="name">
              {{ label }}
            </option>
          </select>
        </div>
        <h4 v-if="workflowDisplayName" class="workflow-name">
          {{ workflowDisplayName }}
        </h4>
        <p class="workflow-blurb">{{ workflowBlurb }}</p>
        <ul uk-accordion="multiple: true">
          <li>
            <a class="uk-accordion-title" href="#">Scan Settings</a>
            <div class="uk-accordion-content">
              <div
                v-for="(setting, index) in workflowSettings"
                :key="'detector_setting' + index"
                class="uk-margin"
              >
                <server-specified-property-control :property-data="setting" />
              </div>
            </div>
          </li>
          <li class="uk-open">
            <a class="uk-accordion-title" href="#">Stitching Settings</a>
            <div class="uk-accordion-content">
              <div class="uk-margin">
                <propertyControl
                  thing-name="smart_scan"
                  property-name="stitch_automatically"
                  label="Automatically Stitch Images Together"
                />
              </div>
              <div class="uk-margin">
                <propertyControl
                  thing-name="smart_scan"
                  property-name="stitch_tiff"
                  label="When Stitching, Produce a Pyramidal TIFF"
                />
              </div>
            </div>
          </li>
        </ul>
        <label class="uk-form-label" for="form-stacked-text">Sample ID</label>
        <div class="uk-form-controls">
          <input v-model="scan_name" class="uk-input uk-form-small" type="text" name="Scan Name" />
        </div>
        <div class="uk-margin">
          <action-button
            ref="smartScanButton"
            thing="smart_scan"
            action="sample_scan"
            :submit-data="{ scan_name: scan_name }"
            submit-label="Start Smart Scan"
            :can-terminate="true"
            @taskStarted="startScanning"
            @beforeUpdate:taskStatus="taskStatus = $event"
            @beforeUpdate:progress="progress = $event"
            @beforeUpdate:log="log = $event"
          />
        </div>
      </div>
      <div v-show="scanning">
        <h2 v-if="displayImageOnRight" style="text-align: center">Live stitching preview</h2>
        <mini-stream-display v-if="displayImageOnRight" />
        <action-log-display id="log-display" :log="log" :task-status="taskStatus" />
        <action-progress-bar :progress="progress" :task-status="taskStatus" />
        <button
          v-if="cancellable"
          type="button"
          class="uk-button uk-button-danger uk-width-1-1"
          @click="$refs.smartScanButton.terminateTask()"
        >
          Cancel
        </button>
        <div v-if="!cancellable" class="uk-margin uk-grid-small uk-child-width-expand" uk-grid>
          <button
            type="button"
            class="uk-button"
            @click="
              scanning = false;
              lastStitchedImage = null;
            "
          >
            Close
          </button>
          <action-button
            thing="smart_scan"
            action="download_zip"
            submit-label="Download ZIP"
            :can-terminate="false"
            :submit-data="{ scan_name: lastScanName }"
            :button-primary="true"
            @response="downloadZipFile"
            @error="modalError"
          />
        </div>
      </div>
      <h3 v-if="scanning">Scan ID: {{ lastScanName }}</h3>
    </div>
    <div class="view-image uk-width-expand uk-height-1-1">
      <img
        v-if="displayImageOnRight"
        id="last-stitched-image"
        class="image-fit"
        :src="lastStitchedImage"
      />
      <streamDisplay v-else />
    </div>
  </div>
</template>

<script>
import streamDisplay from "./streamContent.vue";
import propertyControl from "../labThingsComponents/propertyControl.vue";
import ServerSpecifiedPropertyControl from "../labThingsComponents/serverSpecifiedPropertyControl.vue";
import actionLogDisplay from "../labThingsComponents/actionLogDisplay.vue";
import actionProgressBar from "../labThingsComponents/actionProgressBar.vue";
import MiniStreamDisplay from "../genericComponents/miniStreamDisplay.vue";
import ActionButton from "../labThingsComponents/actionButton.vue";
// vue3 migration
import { useIntersectionObserver } from "@vueuse/core";

export default {
  name: "SlideScanContent",

  components: {
    streamDisplay,
    propertyControl,
    actionLogDisplay,
    actionProgressBar,
    MiniStreamDisplay,
    ActionButton,
    ServerSpecifiedPropertyControl
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
      scan_name: "",
      workflowName: undefined,
      workflowSettings: [],
      workflowDisplayName: undefined,
      workflowBlurb: undefined,
      workflowOptions: [],
    };
  },

  computed: {
    cancellable() {
      return (this.taskStatus == "running") | (this.taskStatus == "pending");
    },
    displayImageOnRight() {
      return this.scanning & (this.lastStitchedImage !== null);
    },
  },

  async created() {
    this.readSettings();
    this.workflowOptions = await this.readThingProperty("smart_scan", "workflow_display_names", true);
  },

  mounted() {
    useIntersectionObserver(
      this.$refs.slideScanView,
      ([{ isIntersecting }]) => {
        this.visibilityChanged(isIntersecting);
      },
      {
        threshold: 0.0,
      },
    );
  },

  methods: {
    visibilityChanged(isVisible) {
      if (isVisible) {
        this.readSettings();
      }
    },
    async readSettings() {
      //this.workflowOptions = await this.readThingProperty("smart_scan", "workflow_display_names", true) || {};

      this.workflowName = await this.readThingProperty("smart_scan", "workflow_name");

      if (!this.workflowName) {
          console.warn("Could not read workflow_name, using default");
          this.workflowName = "histo_scan_workflow";
        }

      if (this.workflowName) {
        console.log("Current workflow name: ", this.workflowName);
        this.ready = await this.readThingProperty(this.workflowName, "ready", true);
        this.workflowSettings = await this.readThingProperty(this.workflowName, "settings_ui", true) || [];
        console.log(this.workflowSettings);
        this.workflowDisplayName = await this.readThingProperty(this.workflowName, "display_name", true);
        this.workflowBlurb = await this.readThingProperty(this.workflowName, "ui_blurb", true);
      }
    },
    onScanError: function (error) {
      this.scanRunning = false;
      this.modalError(error);
    },
    /**
     * Transition the UI into "scanning" mode and begin polling for scan updates.
     *
     * IMPORTANT:
     * This method does NOT start a scan on the server.
     *
     * The <ActionButton> component is responsible for:
     *  - initiating the scan action on the backend when the user clicks the button
     *  - detecting and resuming an already-running scan when the page loads
     *
     * As a result, this method may be invoked in two cases:
     *  1. Immediately after the user clicks "Start Smart Scan"
     *  2. Automatically on page load if <ActionButton> detects an ongoing scan
     *
     * This function only:
     *  - updates local UI state to reflect that scanning is in progress
     *  - clears any previous preview image
     *  - starts the polling loop that fetches scan progress and preview images
     */
    startScanning() {
      console.log("Starting scan...");
      this.lastStitchedImage = null;
      this.scanning = true;
      setTimeout(this.pollScan, 1000);
    },
    async pollScan() {
      console.log("Polling for scan progress...");
      if (this.cancellable) {
        // while the scan is running
        console.log("Polling for scan updates...");
        let mtime = await this.readThingProperty("smart_scan", "latest_preview_stitch_time", true);
        console.log("smart scan latest preview stitch time: ", mtime);
        if (mtime !== null) {
          this.lastStitchedImage = `${this.$store.getters.baseUri}/smart_scan/latest_preview_stitch.jpg?t=${mtime}`;
          console.log("Updated preview image URL: ", this.lastStitchedImage);
        }
        
        this.lastScanName = await this.readThingProperty("smart_scan", "latest_scan_name", true);
        setTimeout(this.pollScan, 1000); // keep rescheduling until it's stopped
      }
    },
    async setWorkflow(name) {
      console.log("Setting workflow to ", name);
      try {
        this.workflowName = name;

        await this.writeThingProperty("smart_scan", "workflow_name", name);

        // refresh  UI
        await this.readSettings();
        console.log("readsettings values: ", this.workflowName, this.workflowSettings, this.workflowDisplayName, this.workflowBlurb);
      } catch (err) {
        this.modalError(err);

        // revert if server rejected
        this.workflowName = await this.readThingProperty("smart_scan", "workflow_name", true);
      }
    },
    async downloadZipFile(response) {
      const scan_name = response.input.scan_name;
      const filename = `${scan_name}_images.zip`;
      const url = response.output.href;
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      console.log(link);
      document.body.appendChild(link);
      link.click();
    },
  },
};
</script>

<style scoped>
#log-display {
  height: 20em;
}
.control-component {
  width: 33%;
}
.workflow-name {
  margin-bottom: 0.5rem;
}
.workflow-blurb {
  color: #a2a2a2;
}
</style>

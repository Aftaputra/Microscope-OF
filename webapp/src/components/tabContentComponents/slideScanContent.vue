<template>
  <actionTab
    thing="smart_scan"
    action="sample_scan"
    :task-id="taskId"
    :task-url="taskUrl"
    :task-info-title="infoPaneTitle"
    :task-info-stream="displayImageOnRight"
    @completed="onScanCompleted"
    @close-task="closeTask"
    @action-started-externally="startScanning"
  >
    <!-- MainView -->
    <img
      v-if="displayImageOnRight"
      id="last-stitched-image"
      class="image-fit"
      :src="lastStitchedImage"
    />
    <streamDisplay v-else />
    <template #controls>
      <slideScanControls />
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
          @task-started="startScanning"
        />
      </div>
    </template>
    <template #task-info>
      <div class="uk-width-1-1 uk-flex uk-flex-center">
        <div class="uk-width-2-3">
          <action-button
            v-if="scanComplete"
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
      <h3 v-if="scanning" class="uk-margin-left">Scan ID: {{ lastScanName }}</h3>
    </template>
  </actionTab>
</template>

<script>
import actionTab from "./actionTab.vue";
import slideScanControls from "./slideScanComponents/slideScanControls.vue";
import streamDisplay from "./streamContent.vue";
import ActionButton from "../labThingsComponents/actionButton.vue";

export default {
  name: "SlideScanContent",

  components: {
    actionTab,
    slideScanControls,
    streamDisplay,
    ActionButton,
  },

  data() {
    return {
      lastScanName: null,
      taskId: null,
      taskUrl: null,
      lastStitchedImage: null,
      scanComplete: false,
      scan_name: "",
    };
  },

  computed: {
    scanning() {
      return this.taskId && this.taskUrl;
    },
    displayImageOnRight() {
      return this.scanning && this.lastStitchedImage !== null;
    },
    infoPaneTitle() {
      if (!this.displayImageOnRight) return null;
      return "Live stitching preview";
    },
  },

  methods: {
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
    startScanning(id, url) {
      this.lastStitchedImage = null;
      this.lastScanName = null;
      this.taskId = id;
      this.taskUrl = url;
      this.scanComplete = false;
      setTimeout(this.pollScan, 1000);
    },
    onScanCompleted() {
      this.scanComplete = true;
    },
    closeTask() {
      this.taskId = null;
      this.taskUrl = null;
      this.lastStitchedImage = null;
      this.scanComplete = false;
    },
    async pollScan() {
      if (!this.scanComplete) {
        // while the scan is running
        let mtime = await this.readThingProperty("smart_scan", "latest_preview_stitch_time", true);
        if (mtime !== null) {
          this.lastStitchedImage = `${this.$store.getters.baseUri}/smart_scan/latest_preview_stitch.jpg?t=${mtime}`;
        }

        this.lastScanName = await this.readThingProperty("smart_scan", "latest_scan_name", true);
        setTimeout(this.pollScan, 1000); // keep rescheduling until it's stopped
      }
    },
    async downloadZipFile(response) {
      const scan_name = response.input.scan_name;
      const filename = `${scan_name}_images.zip`;
      const url = response.output.href;
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
    },
  },
};
</script>

<style scoped></style>

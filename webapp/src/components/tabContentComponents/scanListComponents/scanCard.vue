<template>
  <div class="uk-card">
    <div class="uk-card-body">
      <div class="uk-card-media-top">
        <div class="view-image uk-padding-remove uk-height-1-1">
          <img
            id="thumbnail-stitched-image"
            class="thumbnail-fit"
            :src="thumbnailPath"
            onerror="this.src = '/titleiconpink.svg'"
            @click="requestViewer"
          />
        </div>
      </div>
      <h3 class="uk-card-title scan-card-title">{{ scanData.name }}</h3>
      <h4 v-if="ongoing" class="ongoing-msg">Scan in progress</h4>
      <div v-if="!ongoing" class="button-container">
        <div class="uk-button-group scan-card-buttons">
          <action-button
            class="uk-width-1-2"
            thing="smart_scan"
            action="download_zip"
            submit-label="Download All"
            :can-terminate="false"
            :submit-data="{ scan_name: scanData.name }"
            :button-primary="true"
            @response="downloadZipFile"
            @error="modalError"
          />
          <EndpointButton
            class="uk-width-1-2"
            :button-primary="true"
            :is-disabled="!scanData.stitch_available"
            :url="downloadStitchFile"
            button-label="Download JPEG"
          />
        </div>
        <button class="uk-button uk-button-default uk-width-1-1" @click="deleteScan">Delete</button>
        <action-button
          v-if="scanData.can_stitch | (scanData.stitch_available & !scanData.dzi)"
          submit-label="Stitch Images"
          thing="smart_scan"
          action="stitch_scan"
          :can-terminate="true"
          :submit-data="{ scan_name: scanData.name }"
          :button-primary="false"
          :modal-progress="true"
          @error="modalError"
        />
        <button
          v-if="scanData.dzi"
          class="uk-button uk-button-default uk-width-1-1"
          @click="requestViewer"
        >
          Show Stitched Scan
        </button>
      </div>
      <div class="scan-info">
        <ul>
          <li>{{ scanData.number_of_images }} images</li>
          <li>Created: {{ formatDate(scanData.created) }}</li>
          <li v-if="!ongoing">Duration: {{ formatDuration(scanData.duration) }}</li>
          <li v-if="ongoing">Duration: <i>Ongoing</i></li>
        </ul>
        <ul v-if="!ongoing">
          <li v-if="scanData.number_of_images < 3" class="warning-msg">
            Not enough images to stitch
          </li>
          <li v-else-if="!scanData.dzi && scanData.stitch_available" class="alert-msg">
            Interactive preview not available
          </li>
          <li v-else-if="!scanData.stitch_available" class="alert-msg">
            High quality stitch not available
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import actionButton from "../../labThingsComponents/actionButton.vue";
import EndpointButton from "../../labThingsComponents/endpointButton.vue";

// Export main app
export default {
  name: "ScanCard",
  components: {
    actionButton,
    EndpointButton,
  },

  props: {
    scanData: {
      type: Object,
      required: true,
    },
    scansUri: {
      type: String,
      required: true,
    },
    ongoing: {
      type: Boolean,
      required: true,
    },
  },

  emits: ["viewer-requested", "update-requested"],

  computed: {
    downloadStitchFile() {
      return `${this.$store.getters.baseUri}/smart_scan/get_stitch/${this.scanData.name}`;
    },
    thumbnailPath() {
      return `${this.$store.getters.baseUri}/smart_scan/scans/stitched_thumbnail.jpg?scan_name=${this.scanData.name}&modified=${this.scanData.modified}`;
    },
  },

  methods: {
    formatDate(timestamp) {
      // Multiply by 1000 as JS uses ms not s
      let d = new Date(timestamp * 1000);
      // Convert to a string in a very javascript way!
      let yyyy = d.getFullYear();
      let mm = d.getMonth() + 1;
      let dd = d.getDate();
      let HH = d.getHours().toString().padStart(2, "0");
      let MM = d.getMinutes().toString().padStart(2, "0");
      return `${HH}:${MM} ${dd}/${mm}/${yyyy}`;
    },
    formatDuration(duration) {
      if (duration == null || isNaN(duration)) return "Not known";

      const h = Math.floor(duration / 3600);
      const m = Math.floor((duration % 3600) / 60);
      const s = Math.floor(duration % 60);

      const m_pad = String(m).padStart(2, "0");
      const s_pad = String(s).padStart(2, "0");

      if (h > 0) return `${h}h ${m_pad}m ${s_pad}s`;
      if (m > 0) return `${m_pad}m ${s_pad}s`;
      return `${s_pad}s`;
    },
    requestViewer() {
      // Notify parent that thumbnail was clicked
      if (!this.ongoing) {
        this.$emit("viewer-requested", this.scanData);
      }
    },
    async deleteScan() {
      try {
        await this.modalConfirm(`Are you sure you want to delete ${this.scanData.name}?`);
        await axios.delete(`${this.scansUri}/${this.scanData.name}`);
        this.$emit("update-requested");
        this.modalNotify(`Deleted ${this.scanData.name}`);
      } catch (e) {
        // if the confirmation was cancelled, it's rejected with null error
        if (e) this.modalError(e);
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
<style lang="less" scoped>
ul {
  display: block;
  text-align: center;
  list-style-type: none;
  margin: 5px 0px 10px 0px;
  padding: 0;
}

.warning-msg {
  color: red;
  text-align: center;
  font-weight: bold;
}

.alert-msg {
  color: orange;
  text-align: center;
  font-weight: bold;
}

.scan-card-buttons {
  width: 100%;
}

.scan-card-title {
  text-align: center;
}

.ongoing-msg {
  text-align: center;
  padding: 2rem 0;
}
</style>

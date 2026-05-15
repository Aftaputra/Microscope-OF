<template>
  <div class="uk-card">
    <div class="uk-card-body">
      <div class="uk-card-media-top">
        <div class="view-image uk-padding-remove uk-height-1-1">
          <img
            id="thumbnail-stitched-image"
            :class="[itemData?.dzi ? 'thumbnail-fit clickable' : 'thumbnail-fit disabled']"
            class="thumbnail-fit"
            :src="thumbnailPath"
            onerror="this.src = '/titleiconpink.svg'"
            @click="itemData?.dzi && requestViewer()"
          />
        </div>
      </div>
      <h3 class="uk-card-title gallery-card-title">{{ itemData.name }}</h3>
      <div class="button-container">
        <div class="uk-button-group gallery-card-buttons">
          <action-button
            class="uk-width-1-2"
            thing="smart_scan"
            action="download_zip"
            submit-label="Download All"
            :can-terminate="false"
            :submit-data="{ scan_name: itemData.name }"
            :button-primary="true"
            @response="downloadZipFile"
            @error="modalError"
          />
          <EndpointButton
            class="uk-width-1-2"
            :button-primary="true"
            :is-disabled="!itemData.stitch_available"
            :url="downloadStitchFile"
            button-label="Download JPEG"
          />
        </div>
        <button class="uk-button uk-button-default uk-width-1-1" @click="deleteScan">Delete</button>
        <action-button
          v-if="itemData.can_stitch | (itemData.stitch_available & !itemData.dzi)"
          submit-label="Stitch Images"
          thing="smart_scan"
          action="stitch_scan"
          :can-terminate="true"
          :submit-data="{ scan_name: itemData.name }"
          :button-primary="false"
          :modal-progress="true"
          @error="modalError"
        />
        <button
          v-if="itemData.dzi"
          class="uk-button uk-button-default uk-width-1-1"
          @click="requestViewer"
        >
          Show Stitched Scan
        </button>
      </div>
      <div class="item-info">
        <ul>
          <li>{{ itemData.number_of_images }} images</li>
          <li>Created: {{ formatDate(itemData.created) }}</li>
          <li>Duration: {{ formatDuration(itemData.duration) }}</li>
        </ul>
        <ul>
          <li v-if="itemData.number_of_images < 3" class="warning-msg">
            Not enough images to stitch
          </li>
          <li v-else-if="!itemData.dzi && itemData.stitch_available" class="alert-msg">
            Interactive preview not available
          </li>
          <li v-else-if="!itemData.stitch_available" class="alert-msg">
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
import { mapState } from "pinia";
import { useSettingsStore } from "@/stores/settings.js";

// Export main app
export default {
  name: "GalleryCard",
  components: {
    actionButton,
    EndpointButton,
  },

  props: {
    itemData: {
      type: Object,
      required: true,
    },
  },

  emits: ["viewer-requested", "update-requested"],

  computed: {
    ...mapState(useSettingsStore, ["baseUri"]),
    downloadStitchFile() {
      return `${this.baseUri}/smart_scan/get_stitch/${this.itemData.name}`;
    },
    thumbnailPath() {
      return `${this.baseUri}/smart_scan/scans/stitched_thumbnail.jpg?scan_name=${this.itemData.name}&modified=${this.itemData.modified}`;
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
      this.$emit("viewer-requested", this.itemData);
    },
    async deleteScan() {
      try {
        await this.modalConfirm(`Are you sure you want to delete ${this.itemData.name}?`);
        await axios.delete(`${this.baseUri}/smart_scan/scans/${this.itemData.name}`);
        this.$emit("update-requested");
        this.modalNotify(`Deleted ${this.itemData.name}`);
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
  margin: 5px 0 10px;
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

.gallery-card-buttons {
  width: 100%;
}

.gallery-card-title {
  text-align: center;
}

.thumbnail-fit {
  max-height: 120px;
  max-width: 240px;
  object-fit: contain;
  overflow-y: hidden;
}

.clickable {
  cursor: pointer;
}

.disabled {
  cursor: not-allowed;
}
</style>

<template>
  <div class="uk-card">
    <div class="uk-card-body">
      <div class="uk-card-media-top">
        <div
          class="view-image uk-padding-remove uk-height-1-1"
        >
          <img
            id="thumbnail-stitched-image"
            class="thumbnail-fit"
            :src="thumbnailPath(scanData.name)"
            onerror="this.src='/titleiconpink.svg';"
            @click="requestViewer"
          />
        </div>
      </div>
      <h3 class="uk-card-title" style="text-align: center;">{{ scanData.name }}</h3>
      <div class="button-container">
      <div class="uk-button-group" style="width:100%">
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
          :buttonPrimary=true
          :isDisabled=!scanData.stitch_available
          :URL="downloadStitchFile( scanData.name )"
          buttonLabel="Download JPEG"
          />
      </div>
      <button
        class="uk-button uk-button-default uk-width-1-1"
        @click="deleteScan(scanData.name)"
      >
        Delete
      </button>
      <action-button
        submit-label="Stitch Images"
        thing="smart_scan"
        action="stitch_scan"
        v-if="scanData.can_stitch | (scanData.stitch_available & !scanData.dzi)"
        :can-terminate="true"
        :submit-data="{ scan_name: scanData.name }"
        :button-primary="false"
        :modal-progress="true"
        @error="modalError"
      />
      <button
        v-if="scanData.dzi" class="uk-button uk-button-default uk-width-1-1"
        @click="requestViewer"
      >
      Show Stitched Scan
      </button>
      </div>
      <div>
      <ul>
        <li>{{ scanData.number_of_images }} images</li>
        <li>created: {{ formatDate(scanData.created) }}</li>
        <li>modified: {{ formatDate(scanData.modified) }}</li>
      </ul>
        <li v-if="scanData.number_of_images<3" class="warning-msg">Not enough images to stitch</li>
        <li v-else-if="!scanData.dzi & scanData.stitch_available" class="alert-msg">Interactive preview not available</li> 
        <li v-else-if=!scanData.stitch_available class="alert-msg">High quality stitch not available</li>  
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
  components: { actionButton, EndpointButton },

  props: {
    scanData: {
      type: Object,
      required: true
    },
    scansUri: {
      type: String,
      required: true
    }
  },

  methods: {
    downloadStitchFile: function(name) {
      return `${this.$store.getters.baseUri}/smart_scan/get_stitch/${name}`;
    },
    thumbnailPath(scan_name) {
      return (
        `${this.$store.getters.baseUri}/smart_scan/scans/stitched_thumbnail.jpg?scan_name=` +
        scan_name
      );
    },
    formatDate(timestamp) {
      // Multiply by 1000 as JS uses ms not s
      let d = new Date(timestamp*1000);
      // Convert to a string in a very javascript way!
      let yyyy = d.getFullYear();
      let mm = d.getMonth() + 1;
      let dd = d.getDate();
      let HH = d
        .getHours()
        .toString()
        .padStart(2, "0");
      let MM = d
        .getMinutes()
        .toString()
        .padStart(2, "0");
      return `${HH}:${MM} ${dd}/${mm}/${yyyy}`;
    },
    requestViewer() {
      // Notify parent that thumbnail was clicked
      this.$emit('viewer-requested', this.scanData);
    },
    async deleteScan(name) {
      try {
        await this.modalConfirm(`Are you sure you want to delete ${name}?`);
        await axios.delete(`${this.scansUri}/${name}`);
        this.$emit('update-requested');
        this.modalNotify(`Deleted ${name}`);
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
      console.log(link);
      document.body.appendChild(link);
      link.click();
    }
  }
}
</script>
<style lang="less" scoped>
ul {
  display: inline-block;
  text-align: center;
  list-style-type:none;
  margin: 5px 0px 10px 0px;
}

.warning-msg {
  color: red;
  text-align: center;
  font-weight: bold;
}

.alert-msg{
  color: orange;
  text-align: center;
  font-weight: bold;
}
</style>
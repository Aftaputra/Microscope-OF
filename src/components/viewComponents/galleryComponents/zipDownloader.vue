<template>
  <div v-if="zipBuilderUri">
    <div v-show="downloadReady">
      <button
        :disabled="isDownloading"
        type="button"
        class="uk-button uk-button-default uk-form-small"
        @click="downloadWithAxios()"
      >
        {{ isDownloading ? "Downloading..." : "Download" }}
      </button>
    </div>
    <div v-show="!downloadReady">
      <taskSubmitter
        v-if="zipBuilderUri"
        :can-terminate="false"
        :submit-url="zipBuilderUri"
        :submit-label="'Create ZIP'"
        :submit-data="captureIds"
        @submit="onSubmit"
        @response="onResponse"
        @error="onError"
      >
      </taskSubmitter>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import taskSubmitter from "../../genericComponents/taskSubmitter";

// Export main app
export default {
  name: "ZipDownloader",

  components: {
    taskSubmitter
  },

  props: {
    captureIds: {
      type: Array,
      required: true
    }
  },

  data: function() {
    return {
      isDownloading: false,
      downloadReady: false,
      downloadUrl: null,
      zipBuilderUri: null,
      zipGetterUri: null,
      lastSessionId: null
    };
  },

  computed: {
    pluginsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/plugins`;
    }
  },

  mounted() {
    this.updateZipperUri();
  },

  methods: {
    updateZipperUri: function() {
      axios
        .get(this.pluginsUri) // Get a list of plugins
        .then(response => {
          var plugins = response.data;
          // if ZipBuilderPlugin is enabled
          if ("ZipBuilderPlugin" in plugins) {
            // Get plugin action link
            var builderLink = plugins.ZipBuilderPlugin.views.build.links.self;
            var getterLink = plugins.ZipBuilderPlugin.views.get.links.self;
            // Store plugin action URI
            this.zipBuilderUri = `${this.$store.getters.baseUri}${builderLink}`;
            this.zipGetterUri = `${this.$store.getters.baseUri}${getterLink}`;
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    resetZipper: function() {
      this.downloadReady = false;
    },

    forceFileDownload(response) {
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${this.lastSessionId}.zip`); //or any other extension
      document.body.appendChild(link);
      link.click();
    },

    downloadWithAxios() {
      this.isDownloading = true;
      axios
        .get(this.downloadUrl, { responseType: "arraybuffer" })
        .then(response => {
          this.forceFileDownload(response);
          this.deleteLastZip();
          this.resetZipper();
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        })
        .finally(() => {
          this.isDownloading = false;
        });
    },

    deleteLastZip() {
      axios
        .delete(this.downloadUrl)
        .then(response => {
          console.log(response);
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    onResponse: function(response) {
      this.lastSessionId = response.return;
      this.downloadUrl = `${this.zipGetterUri}/${this.lastSessionId}`;
      this.downloadReady = true;
    },

    onSubmit: function(submitData) {
      console.log("SUBMITTED");
      console.log(submitData);
    },

    onError: function(error) {
      this.modalError(error); // Let mixin handle error
    }
  }
};
</script>

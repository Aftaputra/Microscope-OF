<template>
  <div
    v-observe-visibility="visibilityChanged"
    class="galleryDisplay uk-padding uk-padding-remove-top"
  >
    <!-- Gallery nav bar -->
    <nav class="gallery-navbar uk-navbar-container uk-navbar-transparent" uk-navbar="mode: click">
      <!-- Right side buttons -->
      <div class="uk-navbar-right">
        <div class="uk-grid">
          <div class="scan-list-button">
            <action-button
              class="uk-width-1-1"
              thing="smart_scan"
              action="stitch_all_scans"
              submit-label="Stitch All Remaining"
              :can-terminate="true"
              :button-primary="false"
              :modal-progress="true"
              :requires-confirmation="true"
              :confirmation-message="'<h3>Stitch all unstitched scans?</h3><br>Depending on the number and size of scans, this may be slow, and your microscope should not be used during the stitching.'"
              @error="modalError"
            />
          </div>
          <div>
            <button
              class="uk-button uk-button-default uk-width-1-1 scan-list-button"
              type="button"
              @click="deleteAllScans()"
            >
              Delete All Scans
            </button>
          </div>
          <div>
            <button
              class="uk-button uk-button-default uk-width-1-1 scan-list-button"
              type="button"
              @click="updateScans()"
            >
              Refresh Scans
            </button>
          </div>
        </div>
      </div>
    </nav>

    <ScanViewerModal
      ref="scanViewer"
      :selected-scan="selectedScan"
      :base-uri="$store.getters.baseUri"
    />

    <!-- Gallery -->
    <div
      v-if="$store.getters.ready"
      class="uk-padding-remove-top"
      uk-lightbox="toggle: .lightbox-link"
    >
      <!-- Gallery capture cards -->
      <div class="gallery-grid uk-grid-match" uk-grid>
        <div v-if="scansEmpty">
          <h2>No scans available</h2>
          <p>There are no scans available to show.</p>
        </div>
        <div v-for="scanData in paginatedScans" :key="scanData.id">
          <scan-card
            :scan-data="scanData"
            :scans-uri="scansUri"
            :ongoing="isOngoing(scanData.name)"
            @viewer-requested="showScan"
            @update-requested="updateScans"
          />
        </div>
      </div>
    </div>
    <div v-if="totalPages > 1" class="pagination-container uk-margin-top uk-flex uk-flex-center">
      <ul class="uk-pagination">
        <li :class="{ 'uk-disabled': currentPage === 1 }">
          <a href="#" @click.prevent="changePage(currentPage - 1)">
            <span uk-pagination-previous></span>
          </a>
        </li>

        <li v-for="page in totalPages" :key="page" :class="{ 'uk-active': page === currentPage }">
          <a href="#" @click.prevent="changePage(page)">{{ page }}</a>
        </li>

        <li :class="{ 'uk-disabled': currentPage === totalPages }">
          <a href="#" @click.prevent="changePage(currentPage + 1)">
            <span uk-pagination-next></span>
          </a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import actionButton from "../labThingsComponents/actionButton.vue";
import scanCard from "./scanListComponents/scanCard.vue";
import ScanViewerModal from "./scanListComponents/scanViewer.vue";

// Export main app
export default {
  name: "ScanListContent",
  components: { actionButton, scanCard, ScanViewerModal },

  data: function () {
    return {
      scans: [],
      ongoing: null,
      selectedScan: null,
      osdViewer: null,
      currentPage: 1,
      itemsPerPage: 18,
    };
  },

  computed: {
    scansUri() {
      return this.$store.getters["wot/thingPropertyUrl"](
        "smart_scan",
        "scans",
        "readproperty",
        true,
      );
    },
    scansEmpty() {
      return this.scans.length == 0;
    },
    selectedScanDZI() {
      if (this.selectedScan && this.selectedScan.dzi != "") {
        return `${this.$store.getters.baseUri}/scans/${this.selectedScan.name}/images/${this.selectedScan.dzi}`;
      } else {
        return null;
      }
    },
    totalPages() {
      return Math.ceil(this.scans.length / this.itemsPerPage);
    },
    paginatedScans() {
      const start = (this.currentPage - 1) * this.itemsPerPage;
      return this.scans.slice(start, start + this.itemsPerPage);
    },
  },

  async mounted() {
    // Update on mount (does nothing if not connected)
    await this.updateScans();
    // A global signal listener to perform a gallery refresh
    this.$root.$on("globalUpdateScans", () => {
      this.updateScans();
    });
    this.$root.$on("modalClosed", () => {
      // Handle the modal closed event here
      this.updateScans();
    });
  },

  created: function () {
    // Watch for host 'ready', then update status
    this.unwatchStoreFunction = this.$store.watch(
      (state, getters) => {
        return getters.ready;
      },
      (ready) => {
        if (ready) {
          // If the connection is now ready, update capture list
          this.updateScans();
        } else {
          // If the connection is now disconnected, empty capture list
          this.captures = {};
        }
      },
    );
  },

  beforeDestroy() {
    // Remove global signal listener to perform a gallery refresh
    this.$root.$off("globalUpdateScans");
    // Then we call that function here to unwatch
    if (this.unwatchStoreFunction) {
      this.unwatchStoreFunction();
      this.unwatchStoreFunction = null;
    }
    this.$root.$off("modalClosed"); // Clean up event listener
  },

  methods: {
    visibilityChanged(isVisible) {
      if (isVisible) {
        this.updateScans();
      }
    },
    async updateScans() {
      try {
        let scans_information = await this.readThingProperty("smart_scan", "scans");
        let scans = scans_information.scans;
        this.ongoing = scans_information.ongoing;
        if (!scans | (scans.length == 0)) {
          this.scans = scans;
        }
        scans.forEach((scan) => {
          scan.can_stitch = !scan.stitch_available && scan.number_of_images > 3;
        });
        scans.sort((a, b) => {
          return b.modified - a.modified;
        });
        this.scans = scans;
      } catch (err) {
        console.error("Failed to refresh scans");
        console.error(err);
        this.scans = [];
      }
    },
    isOngoing(name) {
      return name === this.ongoing;
    },
    async deleteAllScans() {
      try {
        await this.modalConfirm(
          "Are you sure you want to delete all scans from the microscope? " +
            "This is <b>irreversible</b>!",
        );
        await axios.delete(`${this.scansUri}`);
        await this.updateScans();
        this.modalNotify("Deleted all scans.");
      } catch (e) {
        // if the confirmation was cancelled, it's rejected with null error
        if (e) this.modalError(e);
      }
    },
    showScan(scan) {
      if (scan.dzi) {
        this.selectedScan = scan;
        this.$refs.scanViewer.show();
      } else {
        this.modalError("Scan not stitched for viewing in webapp, please download or stitch");
      }
    },
    changePage(page) {
      if (page >= 1 && page <= this.totalPages && this.currentPage != page) {
        this.$emit("scrollTop");
        this.currentPage = page;
      }
    },
  },
};
</script>

<style lang="less" scoped>
.gallery-navbar {
  border-width: 0 0 1px 0;
  border-style: solid;
  border-color: rgba(180, 180, 180, 0.25);
}

.gallery-navbar,
.gallery-folder-heading {
  margin-bottom: 30px;
}

.scan-list-button {
  margin-top: 5px;
  margin-bottom: 2px;
}

.pagination-container {
  text-align: center;
}
</style>

<template>
  <div ref="galleryDisplay" class="galleryDisplay uk-padding uk-padding-remove-top">
    <!-- Gallery nav bar -->
    <nav class="gallery-navbar uk-navbar-container uk-navbar-transparent" uk-navbar="mode: click">
      <!-- Right side buttons -->
      <div class="uk-navbar-right">
        <div class="uk-grid">
          <div class="gallery-button">
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
              class="uk-button uk-button-default uk-width-1-1 gallery-button"
              type="button"
              @click="deleteAllScans()"
            >
              Delete All Scans
            </button>
          </div>
          <div>
            <button
              class="uk-button uk-button-default uk-width-1-1 gallery-button"
              type="button"
              @click="refreshGallery()"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>
    </nav>

    <ScanViewerModal ref="scanViewer" :selected-scan="selectedScan" :base-uri="baseUri" />

    <!-- Gallery -->
    <div v-if="ready" class="uk-padding-remove-top" uk-lightbox="toggle: .lightbox-link">
      <!-- Gallery capture cards -->
      <div class="gallery-grid uk-grid-match" uk-grid>
        <div v-if="noItems">
          <h2>Nothing to show</h2>
          <p>There is no captured data to show..</p>
        </div>
        <div v-for="itemData in paginatedItems" :key="itemData.id">
          <gallery-card
            :item-data="itemData"
            @viewer-requested="showScan"
            @update-requested="refreshGallery"
          />
        </div>
      </div>
    </div>
    <PaginateLinks
      :total-pages="numberOfPages"
      :current-page="currentPage"
      @change-page="changePage"
    />
  </div>
</template>

<script>
import axios from "axios";
import PaginateLinks from "@/components/genericComponents/paginateLinks.vue";
import actionButton from "../labThingsComponents/actionButton.vue";
import galleryCard from "./galleryComponents/galleryCard.vue";
import ScanViewerModal from "./galleryComponents/scanViewer.vue";
import { eventBus } from "../../eventBus.js";
import { useIntersectionObserver } from "@vueuse/core";
import { useSettingsStore } from "@/stores/settings.js";
import { mapState, storeToRefs } from "pinia";
import { watch } from "vue";

// Export main app
export default {
  name: "GalleryContent",
  components: {
    actionButton,
    galleryCard,
    ScanViewerModal,
    PaginateLinks,
  },

  emits: ["scrollTop"],

  data: function () {
    return {
      all_items: [],
      selectedScan: null,
      osdViewer: null,
      currentPage: 1,
      itemsPerPage: 18,
    };
  },

  computed: {
    ...mapState(useSettingsStore, ["baseUri", "ready"]),
    scansUri() {
      // The scans URI is currently used for creating endpoint URIs.
      // The actual property does not exist. So allowUndefined=true
      return this.thingPropertyUrl("smart_scan", "scans", true);
    },
    noItems() {
      return !this.all_items || this.all_items?.length === 0;
    },
    selectedScanDZI() {
      if (this.selectedScan && this.selectedScan.dzi != "") {
        return `${this.baseUri}/data/smart_scan/${this.selectedScan.name}/images/${this.selectedScan.dzi}`;
      } else {
        return null;
      }
    },
    // name changed as paginateLinks has the prop totalPages
    numberOfPages() {
      return Math.ceil((this.all_items?.length || 0) / this.itemsPerPage);
    },
    paginatedItems() {
      const start = (this.currentPage - 1) * this.itemsPerPage;
      return (this.all_items || []).slice(start, start + this.itemsPerPage);
    },
  },

  async mounted() {
    const store = useSettingsStore();
    const { ready } = storeToRefs(store);
    this.unwatchStoreFunction = watch(ready, (isReady) => {
      if (isReady) {
        this.refreshGallery();
      } else {
        this.all_items = [];
      }
    });
    useIntersectionObserver(
      this.$refs.galleryDisplay,
      ([{ isIntersecting }]) => {
        this.visibilityChanged(isIntersecting);
      },
      {
        threshold: 0.0, // Adjust as needed
      },
    );
    // Update on mount (does nothing if not connected)
    await this.refreshGallery();
    // A global signal listener to perform a gallery refresh
    eventBus.on("globalRefreshGallery", this.refreshGallery);
    // Handle the modal closed event here
    eventBus.on("modalClosed", this.refreshGallery);
  },

  beforeUnmount() {
    // Remove global signal listener to perform a gallery refresh
    eventBus.off("globalRefreshGallery", this.refreshGallery);
    // Then we call that function here to unwatch
    if (this.unwatchStoreFunction) {
      this.unwatchStoreFunction();
      this.unwatchStoreFunction = null;
    }
    eventBus.off("modalClosed", this.refreshGallery); // Clean up event listener
  },

  methods: {
    visibilityChanged(isVisible) {
      if (isVisible) {
        this.refreshGallery();
      }
    },
    async refreshGallery() {
      try {
        let all_items = await this.readThingProperty("gallery", "list_data");
        // if all_items is not or the number of items in all_items is zero then
        // all_items is equal to empty list.
        // stop refresh gallery as all_items is empty list.
        if (!all_items || all_items?.length === 0) {
          this.all_items = [];
          return;
        }
        all_items.forEach((item) => {
          item.can_stitch = !item.stitch_available && item.number_of_images > 3;
        });
        all_items.sort((a, b) => {
          return b.created - a.created;
        });
        this.all_items = all_items;
        console.debug("Gallery size: %s", this.all_items.length);
      } catch (err) {
        console.error("Failed to refresh gallery items.");
        console.error(err);
        this.all_items = [];
      }
    },
    async deleteAllScans() {
      try {
        await this.modalConfirm(
          "Are you sure you want to delete all scans from the microscope? " +
            "This is <b>irreversible</b>!",
        );
        await axios.delete(`${this.scansUri}`);
        await this.refreshGallery();
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
  border-width: 0 0 1px;
  border-style: solid;
  border-color: rgba(180, 180, 180, 0.25);
}

.gallery-navbar,
.gallery-folder-heading {
  margin-bottom: 30px;
}

.gallery-button {
  margin-top: 5px;
  margin-bottom: 2px;
}
</style>

<template>
  <div ref="galleryDisplay" class="galleryDisplay uk-padding uk-padding-remove-top">
    <!-- Gallery nav bar -->
    <nav class="gallery-navbar uk-navbar-container uk-navbar-transparent" uk-navbar="mode: click">
      <!-- Right side buttons -->
      <div class="uk-navbar-right">
        <div class="uk-grid">
          <div class="gallery-button">
            <multi-select-dropdown
              v-model="selectedCardTypes"
              :options="allCardTypes"
              title="Filter Gallery"
            />
          </div>
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
          <div class="gallery-button">
            <action-button
              class="uk-width-1-1"
              thing="gallery"
              action="delete_all_data"
              submit-label="Delete All"
              :can-terminate="true"
              :button-primary="false"
              :modal-progress="true"
              :requires-confirmation="true"
              :confirmation-message="'<p>Are you sure you want to delete all gallery data from the microscope?</p><p>This is <b>irreversible</b>!</p>'"
              @error="modalError"
            />
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

    <gallery-modal ref="viewerModal" :selected-item="selectedItem" :base-uri="baseUri" />

    <!-- Gallery -->
    <div v-if="ready" class="uk-padding-remove-top" uk-lightbox="toggle: .lightbox-link">
      <!-- Gallery capture cards -->
      <div class="gallery-grid uk-grid-match" uk-grid>
        <div v-if="noItems">
          <h2>Nothing to show</h2>
          <p>There is no captured data to show.</p>
        </div>
        <div v-for="itemData in paginatedItems" :key="itemData.id">
          <gallery-card
            :item-data="itemData"
            @viewer-requested="showItem"
            @update-requested="refreshGallery"
          />
        </div>
      </div>
    </div>
    <PaginateLinks
      :total-pages="totalPages"
      :current-page="currentPage"
      @change-page="changePage"
    />
  </div>
</template>

<script>
import PaginateLinks from "@/components/genericComponents/paginateLinks.vue";
import MultiSelectDropdown from "@/components/genericComponents/multiSelectDropdown.vue";
import actionButton from "../labThingsComponents/actionButton.vue";
import galleryCard from "./galleryComponents/galleryCard.vue";
import galleryModal from "./galleryComponents/galleryViewer.vue";
import { eventBus } from "../../eventBus.js";
import { useIntersectionObserver } from "@vueuse/core";
import { useSettingsStore } from "@/stores/settings.js";
import { mapState } from "pinia";

// Export main app
export default {
  name: "GalleryContent",
  components: {
    actionButton,
    galleryCard,
    galleryModal,
    PaginateLinks,
    MultiSelectDropdown,
  },

  emits: ["scrollTop"],

  data: function () {
    return {
      all_items: [],
      selectedItem: null,
      osdViewer: null,
      currentPage: 1,
      itemsPerPage: 18,
      selectedCardTypes: [],
      allCardTypes: [],
    };
  },

  computed: {
    ...mapState(useSettingsStore, ["baseUri", "ready"]),
    filtered_items() {
      return this.all_items.filter((item) => this.selectedCardTypes.includes(item.card_type));
    },
    noItems() {
      return !this.filtered_items || this.filtered_items?.length === 0;
    },
    totalPages() {
      return Math.ceil((this.filtered_items?.length || 0) / this.itemsPerPage);
    },
    paginatedItems() {
      const start = (this.currentPage - 1) * this.itemsPerPage;
      return (this.filtered_items || []).slice(start, start + this.itemsPerPage);
    },
  },

  watch: {
    totalPages(newPageCount) {
      if (this.currentPage > newPageCount) {
        this.currentPage = Math.max(1, newPageCount);
      } else if (this.currentPage < 1) {
        this.currentPage == 1;
      }
    },
  },

  async mounted() {
    useIntersectionObserver(
      this.$refs.galleryDisplay,
      ([{ isIntersecting }]) => {
        this.visibilityChanged(isIntersecting);
      },
      {
        threshold: 0.0, // Adjust as needed
      },
    );
    this.allCardTypes = await this.readThingProperty("gallery", "card_types");
    this.selectedCardTypes = this.allCardTypes;
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
        // if all_items is "falsey" or the number of items in all_items is zero then
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
      } catch (err) {
        console.error("Failed to refresh gallery items.");
        console.error(err);
        this.all_items = [];
      }
    },
    showItem(itemData) {
      if (itemData.card_type === "Scan") {
        if (itemData.dzi) {
          this.selectedItem = itemData;
          this.$refs.viewerModal.show();
        } else {
          this.modalError("Scan not stitched for viewing in webapp, please download or stitch");
        }
      } else {
        this.selectedItem = itemData;
        this.$refs.viewerModal.show();
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

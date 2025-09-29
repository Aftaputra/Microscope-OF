<template>
  <div
    v-observe-visibility="visibilityChanged"
    class="galleryDisplay uk-padding uk-padding-remove-top">
    <!-- Gallery nav bar -->
    <nav
      class="gallery-navbar uk-navbar-container uk-navbar-transparent"
      uk-navbar="mode: click"
    >
      <!-- Right side buttons -->
      <div class="uk-navbar-right">
        <div class="uk-grid">
        <div style="margin-top:5px;margin-bottom: 2px">
            <action-button
                class="uk-width-1-1"
                thing="smart_scan"
                action="stitch_all_scans"
                submit-label="Stitch All Remaining"
                :can-terminate="true"
                :button-primary="false"
                :modal-progress="true"
                :requires-confirmation="true"
                :confirmation-message="
                  '<h3>Stitch all unstitched scans?</h3><br>Depending on the number and size of scans, this may be slow, and your microscope should not be used during the stitching.'
                "
                @error="modalError"
                />
          </div>
          <div>
            <button
              class="uk-button uk-button-default uk-width-1-1"
              style="margin-top:5px;margin-bottom: 2px"
              type="button"
              @click="deleteAllScans()"
            >
              Delete All Scans
            </button>
          </div>
          <div>
            <button
              class="uk-button uk-button-default uk-width-1-1"
              style="margin-top:5px;margin-bottom: 2px"
              type="button"
              @click="updateScans()"
            >
              Refresh Scans
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Modal for scan display -->
    <div id="scan-modal" ref="scanModal" style="padding: 10px;" uk-modal>
      <div class="uk-modal-dialog uk-modal-body " v-if="selectedScan" style="padding: 10px; width: 95%; height: 95%;">
        <h2 class="uk-modal-title">
          {{ selectedScan.name }}
          <button class="uk-modal-close uk-float-right" type="button"><span class="material-symbols-outlined">close</span></button>
          <button class="uk-float-right" type="button" @click="goFullscreen">
            <span class="material-symbols-outlined">fullscreen</span>
          </button>
          </h2>
          <div v-if="selectedScanDZI" id="viewer_container" style="height: 80%;">
            <OpenSeadragonViewer
              id="openseadragon"
              ref="openseadragon"
              :src="selectedScanDZI"
            />
          </div>
      </div>
    </div>

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
          <p>
            There are no scans available to show.
          </p>
        </div>
        <div v-for="scanData in scans" :key="scanData.id">
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
  </div>
</template>

<script>
import axios from "axios";
import UIkit from "uikit";
import actionButton from "../labThingsComponents/actionButton.vue";
import scanCard from "./scanListComponents/scanCard.vue";
import OpenSeadragonViewer from "./scanListComponents/openSeadragonViewer.vue";

// Export main app
export default {
  name: "ScanListContent",
  components: { actionButton, OpenSeadragonViewer, scanCard },

  data: function() {
    return {
      scans: [],
      ongoing: null,
      selectedScan: null,
      osdViewer: null
    };
  },

  computed: {
    scansUri() {
      return this.$store.getters["wot/thingPropertyUrl"](
        "smart_scan",
        "scans",
        "readproperty",
        true
      );
    },
    scansEmpty() {
      return this.scans.length == 0;
    },
    selectedScanDZI() {
      if (this.selectedScan && this.selectedScan.dzi!="") {
        return `${this.$store.getters.baseUri}/scans/${this.selectedScan.name}/images/${this.selectedScan.dzi}`;
      } else {
        return null;
      }
    }
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

  created: function() {
    // Watch for host 'ready', then update status
    this.unwatchStoreFunction = this.$store.watch(
      (state, getters) => {
        return getters.ready;
      },
      ready => {
        if (ready) {
          // If the connection is now ready, update capture list
          this.updateScans();
        } else {
          // If the connection is now disconnected, empty capture list
          this.captures = {};
        }
      }
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
    goFullscreen() {
      this.$refs.openseadragon.openFullscreen();
    },
    async updateScans() {
      try {
        let scans_information = await this.readThingProperty("smart_scan", "scans");
        let scans = scans_information.scans
        this.ongoing = scans_information.ongoing
        if (!scans | (scans.length == 0)) {
          this.scans = scans;
        }
        scans.forEach(scan => {
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
      return name === this.ongoing
    },
    async deleteAllScans() {
      try {
        await this.modalConfirm(
          "Are you sure you want to delete all scans from the microscope? " +
            "This is <b>irreversible</b>!"
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
      if (scan.dzi){
        this.selectedScan = scan;
        UIkit.modal(this.$refs.scanModal).show();
      }
      else {
        this.modalError(`Scan not stitched for viewing in webapp, please download or stitch`)
      }
    }
  }
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

</style>
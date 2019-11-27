<template>
  <div class="galleryDisplay uk-padding uk-padding-remove-top">
    <nav
      class="uk-navbar-container uk-navbar-transparent navbar"
      uk-navbar="mode: click"
    >
      <div
        class="uk-navbar-left uk-padding-remove-top uk-padding-remove-bottom"
      >
        <ul class="uk-navbar-nav">
          <li :class="[sortDescending ? 'uk-active' : '']">
            <a class="uk-icon" href="#" @click="sortDescending = true"
              ><i class="material-icons">keyboard_arrow_down</i></a
            >
          </li>
          <li :class="[!sortDescending ? 'uk-active' : '']">
            <a class="uk-icon" href="#" @click="sortDescending = false"
              ><i class="material-icons">keyboard_arrow_up</i></a
            >
          </li>
          <li>
            <a href="#">Filter</a>
            <div
              class="uk-navbar-dropdown"
              :class="{
                'uk-light uk-background-secondary':
                  $store.state.globalSettings.darkMode
              }"
            >
              <ul class="uk-nav uk-navbar-dropdown-nav">
                <form class="uk-form-stacked">
                  <div
                    v-for="tag in allTags"
                    :key="tag"
                    class="uk-margin-small"
                  >
                    <label
                      ><input
                        :id="tag"
                        v-model="checkedTags"
                        class="uk-checkbox"
                        type="checkbox"
                        :value="tag"
                        checked
                      />
                      {{ tag }}</label
                    >
                  </div>
                </form>
              </ul>
            </div>
          </li>
        </ul>
      </div>
    </nav>

    <div
      v-if="$store.getters.ready"
      class="uk-padding-remove-top"
      uk-lightbox="toggle: .lightbox-link"
    >
      <div
        v-if="galleryFolder"
        class="uk-flex uk-flex-middle uk-padding uk-padding-remove-horizontal uk-padding-remove-bottom"
      >
        <a href="#" class="uk-icon uk-margin-remove" @click="galleryFolder = ''"
          ><i class="material-icons">arrow_back</i></a
        >
        <div class="uk-margin-left">
          <h3 class="uk-margin-remove uk-margin-left">
            <b>SCAN</b> {{ allScans[galleryFolder].metadata.filename }}
          </h3>
        </div>
      </div>

      <div class="uk-grid-medium uk-grid-match uk-margin-top" uk-grid>
        <div v-for="item in sortedItems" :key="item.metadata.id">
          <scanCard
            v-if="'isScan' in item"
            :metadata="item.metadata"
            :thumbnail="item.thumbnail"
          />
          <captureCard v-else :capture-state="item" />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import captureCard from "./galleryComponents/captureCard.vue";
import scanCard from "./galleryComponents/scanCard.vue";

// Export main app
export default {
  name: "GalleryDisplay",

  components: {
    captureCard,
    scanCard
  },

  data: function() {
    return {
      captures: {},
      checkedTags: [],
      sortDescending: true,
      galleryFolder: "",
      scanTag: "scan",
      unwatchStoreFunction: null
    };
  },

  computed: {
    capturesUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/captures`;
    },
    captureList: function() {
      // List of captures, obtained from this.captures values
      return Object.values(this.captures);
    },
    allTags: function() {
      // Return an array of unique tags across all captures
      var tags = [];
      for (var capture of this.captureList) {
        for (var tag of capture.metadata.tags) {
          if (!tags.includes(tag)) {
            tags.push(tag);
          }
        }
      }
      return tags.sort();
    },

    noScanCaptureList: function() {
      // List of captures that are not part of a scan
      var captures = [];
      for (var capture of this.captureList) {
        // Filter by selected tags
        var tags = capture.metadata.tags;

        // Add to capture list if matched
        if (!tags.includes(this.scanTag)) {
          captures.push(capture);
        }
      }

      return captures;
    },

    allScans: function() {
      // List of scans as capture-like objects
      var scans = {};

      for (var capture of this.captureList) {
        var custom = capture.metadata.custom;
        var tags = capture.metadata.tags;

        if ("scan_id" in custom) {
          var id = custom["scan_id"];

          // If this scan ID hasn't been seen before
          if (!(id in scans)) {
            scans[id] = {};
            scans[id].isScan = true;
            scans[id].captureList = [];
            scans[id].metadata = {
              filename: custom.basename,
              time: custom.time,
              id: custom.scan_id
            };
            scans[id].metadata.tags = [];
            scans[id].metadata.custom = {};
          }

          // Add the capture object to the scan
          scans[id].captureList.push(capture);

          // Add missing scan metadata, prioritising first capture
          for (var key of Object.keys(custom)) {
            if (!(key in scans[id].metadata.custom)) {
              scans[id].metadata.custom[key] = custom[key];
            }
          }

          // Append missing tags
          for (var tag of tags) {
            if (!scans[id].metadata.tags.includes(tag)) {
              scans[id].metadata.tags.push(tag);
            }
          }

          // Create a preview thumbnail
          // TODO: Use URI defined in capture representation
          if (!("thumbnail" in scans[id])) {
            scans[id].thumbnail = `${this.$store.getters.baseUri}${
              capture.links.download
            }?thumbnail=true`;
          }
        }
      }
      return scans;
    },

    scanList: function() {
      // List of scans, obtained from this.allScans values
      return Object.values(this.allScans);
    },

    itemList: function() {
      // Get list of current items to show
      // If galleryFolder (ie inside a scan folder), show scan captures
      // Otherwise, show root captures and scan cards
      if (this.galleryFolder) {
        console.log(this.allScans[this.galleryFolder].captureList);
        return this.allScans[this.galleryFolder].captureList;
      } else {
        return this.noScanCaptureList.concat(this.scanList);
      }
    },

    filteredItems: function() {
      // Filter itemList by checkedTags
      return this.filterCaptureList(this.itemList, this.checkedTags);
    },

    sortedItems: function() {
      // Sort filteredItems using sortCaptureList function
      return this.sortCaptureList(this.filteredItems);
    }
  },

  mounted() {
    // A global signal listener to perform a gallery refresh
    this.$root.$on("globalUpdateCaptureList", () => {
      this.updateCaptureList();
    });
    // A global signal listener to set the gallery folder
    this.$root.$on("globalUpdateCaptureFolder", folder => {
      this.galleryFolder = folder;
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
          this.updateCaptureList();
        } else {
          // If the connection is now disconnected, empty capture list
          this.captures = {};
        }
      }
    );
  },

  beforeDestroy() {
    // Then we call that function here to unwatch
    if (this.unwatchStoreFunction) {
      this.unwatchStoreFunction();
      this.unwatchStoreFunction = null;
    }
  },

  methods: {
    updateCaptureList: function() {
      console.log("Updating capture list...");
      axios
        .get(this.capturesUri)
        .then(response => {
          this.captures = response.data;
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    filterCaptureList: function(list, filterTags) {
      // Filter a list of captures by an array of tags
      var result = [];
      for (var capture of list) {
        // Assume exclusion
        var includeCapture = false;

        // Filter by selected tags
        var tags = capture.metadata.tags;
        let checker = (arr, target) => target.every(v => arr.includes(v));
        // True if all tags match
        includeCapture = checker(tags, filterTags);

        // Add to capture list if matched
        if (includeCapture == true) {
          result.push(capture);
        }
      }

      return result;
    },

    sortCaptureList: function(list) {
      // Sort a list of captures by metadata time
      function compare(a, b) {
        if (a.metadata.time < b.metadata.time) return -1;
        if (a.metadata.time > b.metadata.time) return 1;
        return 0;
      }

      if (this.sortDescending == true) {
        return list.sort(compare).reverse();
      } else {
        return list.sort(compare);
      }
    }
  }
};
</script>

<style scoped lang="less">
.navbar {
  border-width: 0 0 1px 0;
  border-style: solid;
  border-color: rgba(180, 180, 180, 0.25);
}
</style>

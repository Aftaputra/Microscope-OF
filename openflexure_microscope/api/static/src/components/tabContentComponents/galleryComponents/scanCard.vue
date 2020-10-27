<template>
  <div
    class="capture-card uk-card uk-card-primary uk-padding-remove uk-width-medium"
  >
    <div class="uk-card-media-top">
      <a href="#">
        <img
          class="uk-width-1-1"
          :data-src="scanState.thumbnail"
          :alt="scanState.metadata.image.id"
          width="300"
          height="225"
          uk-img
          @click="onClick"
        />
      </a>
    </div>

    <div class="uk-card-body uk-padding-small">
      <div
        class="uk-width-1-1 uk-margin-small uk-margin-remove-left uk-margin-remove-right"
        uk-grid
      >
        <div class="uk-margin-remove-top uk-padding-remove uk-width-expand">
          <b>{{ scanState.metadata.type || "Dataset" }}: </b>
          {{ scanState.metadata.image.name }}
        </div>
        <div class="uk-margin-remove-top uk-padding-remove uk-width-auto">
          <a href="#" class="uk-icon" @click="delAllConfirm()">
            <i class="material-icons">delete</i>
          </a>
        </div>
      </div>

      <div
        class="uk-text-meta uk-margin-remove-top uk-padding-remove uk-width-expand"
      >
        <time>{{ scanState.metadata.image.acquisitionDate }}</time>
      </div>
      <div
        class="uk-text-meta uk-margin-remove-top uk-padding-remove uk-width-auto"
      >
        <a :href="metadataModalTarget" uk-toggle>More...</a>
      </div>
    </div>

    <div class="uk-card-footer uk-padding-small">
      <span
        v-for="tag in scanState.metadata.image.tags"
        :key="tag"
        class="uk-label uk-margin-small-right deletable-label"
      >
        {{ tag }}
      </span>
    </div>

    <div :id="metadataModalID" uk-modal>
      <div class="uk-modal-dialog uk-modal-body">
        <button class="uk-modal-close-default" type="button" uk-close></button>
        <h2 class="uk-modal-title">{{ scanState.metadata.image.name }}</h2>
        <p><b>Time: </b>{{ scanState.metadata.image.acquisitionDate }}</p>
        <p><b>ID: </b>{{ scanState.metadata.image.id }}</p>

        <hr />

        <div
          v-for="(value, key) in scanState.metadata.image.annotations"
          :key="key"
        >
          <p>
            <b>{{ key }}: </b>{{ value }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

// Export main app
export default {
  name: "ScanCard",

  props: {
    scanState: {
      type: Object,
      required: true
    }
  },

  computed: {
    tagModalID: function() {
      return this.makeModalName("tag-modal-");
    },
    tagModalTarget: function() {
      return "#" + this.tagModalID;
    },
    metadataModalID: function() {
      return this.makeModalName("metadata-modal-");
    },
    metadataModalTarget: function() {
      return "#" + this.metadataModalID;
    },
    allURLs: function() {
      var urls = [];
      for (var capture of this.scanState.captures) {
        urls.push(capture.links.self.href);
      }
      return urls;
    }
  },

  methods: {
    onClick: function() {
      this.$emit("selectFolder", this.scanState.metadata.image.id);
    },

    makeModalName: function(prefix) {
      return prefix + this.scanState.metadata.image.id;
    },

    delAllConfirm: function() {
      var context = this;
      this.modalConfirm(
        "Permanantly delete all captures in this dataset?"
      ).then(function() {
        context.deleteAll();
      });
    },

    deleteAll: function() {
      axios.all(this.allURLs.map(l => axios.delete(l))).then(() => {
        // Emit signal to update capture list
        this.$root.$emit("globalUpdateCaptures");
      });
    }
  }
};
</script>

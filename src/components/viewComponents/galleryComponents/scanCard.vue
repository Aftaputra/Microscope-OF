<template>
  <div
    class="captureCard uk-card uk-card-primary uk-card-hover uk-padding-remove uk-width-medium"
  >
    <div class="uk-card-media-top">
      <a href="#">
        <img
          class="uk-width-1-1"
          :data-src="thumbnail"
          :alt="metadata.id"
          width="300"
          height="225"
          uk-img
          @click="$root.$emit('globalUpdateCaptureFolder', metadata.id)"
        />
      </a>
    </div>

    <div class="uk-card-body uk-padding-small">
      <div
        class="uk-width-1-1 uk-margin-small uk-margin-remove-left uk-margin-remove-right"
        uk-grid
      >
        <div class="uk-margin-remove-top uk-padding-remove uk-width-expand">
          <b>{{ metadata.type || "Dataset" }}: </b> {{ metadata.name }}
        </div>
      </div>

      <div
        class="uk-text-meta uk-margin-remove-top uk-padding-remove uk-width-expand"
      >
        <time>{{ metadata.acquisitionDate }}</time>
      </div>
      <div
        class="uk-text-meta uk-margin-remove-top uk-padding-remove uk-width-auto"
      >
        <a :href="metadataModalTarget" uk-toggle>More...</a>
      </div>
    </div>

    <div class="uk-card-footer uk-padding-small">
      <span
        v-for="tag in metadata.tags"
        :key="tag"
        class="uk-label uk-margin-small-right deletable-label"
      >
        {{ tag }}
      </span>
    </div>

    <div :id="metadataModalID" uk-modal>
      <div class="uk-modal-dialog uk-modal-body">
        <button class="uk-modal-close-default" type="button" uk-close></button>
        <h2 class="uk-modal-title">{{ metadata.basename }}</h2>
        <p><b>Time: </b>{{ metadata.acquisitionDate }}</p>
        <p><b>ID: </b>{{ metadata.id }}</p>

        <hr />

        <div v-for="(value, key) in metadata.annotations" :key="key">
          <p>
            <b>{{ key }}: </b>{{ value }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// Export main app
export default {
  name: "CaptureCard",

  props: {
    metadata: {
      type: Object,
      required: true
    },
    thumbnail: {
      type: String,
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
    }
  },

  methods: {
    makeModalName: function(prefix) {
      return prefix + this.metadata.id;
    }
  }
};
</script>

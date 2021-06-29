<template>
  <div
    class="capture-card uk-card uk-card-primary uk-padding-remove uk-width-medium"
  >
    <div class="uk-card-media-top">
      <a href="#">
        <img
          class="uk-width-1-1"
          :data-src="thumbnail"
          :alt="id"
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
          <b>{{ type }}: </b>
          {{ name }}
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
        <time>{{ time }}</time>
      </div>
    </div>

    <div class="uk-card-footer uk-padding-small">
      <button
        v-if="openInImjoyMenuItems.length != 0"
        class="uk-icon"
        type="button"
      >
        <img
          style="width:25px;"
          src="https://imjoy.io/static/img/imjoy-icon.svg"
        />
      </button>
      <div uk-dropdown="pos: top-center">
        <ul class="uk-nav uk-dropdown-nav">
          <li v-for="item in openInImjoyMenuItems" :key="item.name">
            <a
              href="#"
              style="color:black"
              @click="item.callback(name, allURLs)"
              ><i class="material-icons">launch</i>{{ item.title }}</a
            >
          </li>
        </ul>
      </div>
      &nbsp;
      <span
        v-for="tag in tags"
        :key="tag"
        class="uk-label uk-margin-small-right deletable-label"
      >
        {{ tag }}
      </span>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { mapState } from "vuex";

// Export main app
export default {
  name: "ScanCard",

  props: {
    id: {
      type: String,
      required: true
    },
    name: {
      type: String,
      required: true
    },
    time: {
      type: String,
      required: true
    },
    type: {
      type: String,
      required: false,
      default: "Dataset"
    },
    thumbnail: {
      type: String,
      required: true
    },
    captures: {
      type: Array,
      required: true
    },
    tags: {
      type: Array,
      required: false,
      default: function() {
        return [];
      }
    }
  },

  computed: {
    allURLs: function() {
      var urls = [];
      for (var capture of this.captures) {
        urls.push(capture.links.self.href);
      }
      return urls;
    },
    ...mapState("imjoy", { openInImjoyMenuItems: "openScanMenu" })
  },

  methods: {
    onClick: function() {
      this.$emit("selectFolder", this.id);
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

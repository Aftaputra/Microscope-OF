<template>
  <a
    href="#"
    class="uk-link"
    :class="classObject"
    :uk-tooltip="tooltipOptions"
    @click="setThisTab"
  >
    <slot></slot>
    <div class="tabtitle">
      {{ title }}
    </div>
  </a>
</template>

<script>
export default {
  name: "TabIcon",

  props: {
    id: {
      type: String,
      required: true
    },
    currentTab: {
      type: String,
      required: true
    },
    clickCallback: {
      type: Function,
      required: false,
      default: null
    },
    requireConnection: Boolean
  },

  computed: {
    title: function() {
      // Get the last section of a fully qualified name
      var topName = this.id.split(".").pop();
      // Make first character uppercase, then add the rest of the string
      return topName.charAt(0).toUpperCase() + topName.slice(1);
    },

    tooltipOptions: function() {
      return `pos: right; title: ${this.title}; delay: 500`;
    },

    classObject: function() {
      return {
        "tabicon-active": this.currentTab == this.id,
        "uk-disabled": this.requireConnection && !this.$store.getters.ready
      };
    }
  },

  methods: {
    setThisTab(event) {
      this.$emit("set-tab", event, this.id);
      if (this.clickCallback) {
        this.clickCallback();
      }
    }
  }
};
</script>

<style lang="less" scoped>
// Custom UIkit CSS modifications
@import "../../assets/less/theme.less";

.tabicon-active {
  color: @global-primary-background !important;
}

.hook-inverse() {
  .tabicon-active {
    color: @inverse-primary-muted-color !important;
  }
}

.tabtitle {
  max-width: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
}

a:hover,
.uk-link:hover {
  text-decoration: none !important;
}
</style>

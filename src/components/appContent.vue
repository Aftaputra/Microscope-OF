<template>
  <div
    id="app-content"
    class="uk-margin-remove uk-padding-remove uk-height-1-1"
    uk-grid
  >
    <!-- Vertical tab bar -->
    <div
      id="switcher-left"
      class="uk-flex uk-flex-column uk-padding-remove uk-width-auto uk-height-1-1 uk-text-center"
    >
      <tabIcon
        v-show="!liteMode"
        id="connect-tab-icon"
        tab-i-d="connect"
        :require-connection="false"
        :current-tab="currentTab"
        @set-tab="setTab"
      >
        <i class="material-icons">bug_report</i>
      </tabIcon>
      <tabIcon
        id="gallery-tab-icon"
        tab-i-d="gallery"
        :require-connection="true"
        :current-tab="currentTab"
        @set-tab="setTab"
      >
        <i class="material-icons">photo_library</i>
      </tabIcon>

      <hr />

      <tabIcon
        id="navigate-tab-icon"
        tab-i-d="navigate"
        :require-connection="true"
        :current-tab="currentTab"
        @set-tab="setTab"
      >
        <i class="material-icons">gamepad</i>
      </tabIcon>
      <tabIcon
        id="capture-tab-icon"
        tab-i-d="capture"
        :require-connection="true"
        :current-tab="currentTab"
        @set-tab="setTab"
      >
        <i class="material-icons">camera_alt</i>
      </tabIcon>
      <tabIcon
        id="settings-tab-icon"
        tab-i-d="settings"
        :require-connection="false"
        :current-tab="currentTab"
        @set-tab="setTab"
      >
        <i class="material-icons">settings</i>
      </tabIcon>

      <hr id="extension-tab-divider" />

      <tabIcon
        v-for="plugin in pluginsGuiList"
        :key="plugin.id"
        :tab-i-d="plugin.id"
        :title="plugin.title"
        :require-connection="plugin.requiresConnection"
        :current-tab="currentTab"
        :click-callback="updatePlugins"
        @set-tab="setTab"
      >
        <i class="material-icons">{{ plugin.icon || "extension" }}</i>
      </tabIcon>
    </div>

    <!-- Corresponding vertical tab content -->
    <div
      id="container-left"
      class="uk-padding-remove uk-height-1-1 uk-width-expand"
    >
      <tabContent
        tab-i-d="connect"
        :require-connection="false"
        :current-tab="currentTab"
      >
        <connectContent />
      </tabContent>
      <tabContent
        tab-i-d="gallery"
        :require-connection="false"
        :current-tab="currentTab"
      >
        <galleryContent />
      </tabContent>
      <tabContent
        tab-i-d="navigate"
        :require-connection="true"
        :current-tab="currentTab"
      >
        <navigateContent />
      </tabContent>
      <tabContent
        tab-i-d="capture"
        :require-connection="true"
        :current-tab="currentTab"
      >
        <captureContent />
      </tabContent>
      <tabContent
        tab-i-d="settings"
        :require-connection="false"
        :current-tab="currentTab"
      >
        <settingsContent class="section-content" />
      </tabContent>

      <tabContent
        v-for="plugin in pluginsGuiList"
        :key="plugin.id"
        :tab-i-d="plugin.id"
        :require-connection="plugin.requiresConnection"
        :current-tab="currentTab"
      >
        <extensionContent
          :forms="plugin.forms"
          :web-component="plugin.wc"
          :view-panel="plugin.viewPanel"
          @reloadForms="updatePlugins()"
        />
      </tabContent>
    </div>
  </div>
</template>

<script>
import axios from "axios";

// Import generic components
import tabIcon from "./genericComponents/tabIcon";
import tabContent from "./genericComponents/tabContent";

// Import new content components
import connectContent from "./tabContentComponents/connectContent.vue";
import navigateContent from "./tabContentComponents/navigateContent.vue";
import captureContent from "./tabContentComponents/captureContent.vue";
import settingsContent from "./tabContentComponents/settingsContent.vue";
import galleryContent from "./tabContentComponents/galleryContent.vue";
import extensionContent from "./tabContentComponents/extensionContent.vue";

// Export main app
export default {
  name: "PanelLeft",

  components: {
    tabIcon,
    tabContent,
    connectContent,
    navigateContent,
    captureContent,
    settingsContent,
    galleryContent,
    extensionContent
  },

  data: function() {
    return {
      plugins: [],
      currentTab: "connect",
      unwatchStoreFunction: null,
      liteMode: process.env.VUE_APP_LITEMODE == "true" ? true : false
    };
  },

  computed: {
    pluginsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/extensions`;
    },
    pluginsGuiList: function() {
      // List of plugin GUIs, obtained from this.plugins values
      console.log("Recalculating plugins");
      var pluginGuis = [];
      for (let plugin of Object.values(this.plugins)) {
        if (plugin.meta.gui) {
          pluginGuis.push(plugin.meta.gui);
        }
      }
      return pluginGuis;
    }
  },

  created: function() {
    // Watch for host 'ready', then update status
    this.unwatchStoreFunction = this.$store.watch(
      (state, getters) => {
        return getters.ready;
      },
      ready => {
        // Update plugins
        this.updatePlugins();
        if (ready) {
          console.log("Left panel now ready");
        } else {
          console.log("Right panel now disabled");
          this.currentTab = "connect";
        }
      }
    );
  },

  mounted: function() {},

  beforeDestroy() {
    // Then we call that function here to unwatch
    if (this.unwatchStoreFunction) {
      this.unwatchStoreFunction();
      this.unwatchStoreFunction = null;
    }
  },

  methods: {
    updatePlugins: function() {
      console.log("Updating plugin forms");
      axios
        .get(this.pluginsUri)
        .then(response => {
          console.log(response);
          this.plugins = response.data;
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },
    setTab: function(event, tab) {
      if (!(this.currentTab == tab)) {
        this.currentTab = tab;
      }
    }
  }
};
</script>

<style scoped lang="less">
#component-left {
  width: 100%;
  height: 100%;
}

#container-left {
  overflow: hidden;
  background-color: rgba(180, 180, 180, 0.025);
  width: 100%;
  height: 100%;
}

#switcher-left {
  border-width: 0 1px 0 0;
  border-style: solid;
  border-color: rgba(180, 180, 180, 0.25);
}

#switcher-left a {
  padding: 10px 8px;
}

#switcher-left {
  width: 75px;
  background-color: rgba(180, 180, 180, 0.1);
  padding-top: 2px !important;
}
</style>

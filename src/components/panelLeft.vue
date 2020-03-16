<template>
  <div
    id="panel-left"
    class="uk-margin-remove uk-padding-remove uk-height-1-1"
    uk-grid
  >
    <!-- Vertical tab bar -->
    <div
      id="switcher-left"
      class="uk-flex uk-flex-column uk-padding-remove uk-width-auto uk-height-1-1 uk-text-center"
    >
      <tabIcon
        id="status"
        :require-connection="false"
        :current-tab="currentTab"
        @set-tab="setTab"
      >
        <i class="material-icons">bug_report</i>
      </tabIcon>
      <tabIcon
        id="navigate"
        :require-connection="true"
        :current-tab="currentTab"
        @set-tab="setTab"
      >
        <i class="material-icons">gamepad</i>
      </tabIcon>
      <tabIcon
        id="capture"
        :require-connection="true"
        :current-tab="currentTab"
        @set-tab="setTab"
      >
        <i class="material-icons">camera_alt</i>
      </tabIcon>
      <tabIcon
        id="settings"
        :require-connection="false"
        :current-tab="currentTab"
        @set-tab="setTab"
      >
        <i class="material-icons">settings</i>
      </tabIcon>

      <hr />

      <tabIcon
        v-for="plugin in pluginsGuiList"
        :id="plugin.id"
        :key="plugin.id"
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
      <div
        id="component-left"
        class="uk-padding-remove uk-flex uk-flex-1 panel-content"
      >
        <tabContent
          id="status"
          :require-connection="false"
          :current-tab="currentTab"
        >
          <paneStatus />
        </tabContent>
        <tabContent
          id="navigate"
          :require-connection="true"
          :current-tab="currentTab"
        >
          <paneNavigate />
        </tabContent>
        <tabContent
          id="capture"
          :require-connection="true"
          :current-tab="currentTab"
        >
          <paneCapture />
        </tabContent>
        <tabContent
          id="settings"
          :require-connection="false"
          :current-tab="currentTab"
        >
          <paneSettings />
        </tabContent>

        <tabContent
          v-for="plugin in pluginsGuiList"
          :id="plugin.id"
          :key="plugin.id"
          :require-connection="plugin.requiresConnection"
          :current-tab="currentTab"
        >
          <div
            v-for="form in plugin.forms"
            :key="
              `${form.route}/${form.name}`.replace(/\s+/g, '-').toLowerCase()
            "
            class="uk-flex uk-flex-column"
          >
            <JsonForm
              :name="form.name"
              :route="form.route"
              :is-task="form.isTask"
              :submit-label="form.submitLabel"
              :schema="form.schema"
              :emit-on-response="form.emitOnResponse"
              @reloadForms="updatePlugins()"
            />
            <hr />
          </div>
        </tabContent>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

// Import generic components
import tabIcon from "./genericComponents/tabIcon";
import tabContent from "./genericComponents/tabContent";

// Import control components
import paneStatus from "./controlComponents/paneStatus";
import paneNavigate from "./controlComponents/paneNavigate";
import paneCapture from "./controlComponents/paneCapture";
import paneSettings from "./controlComponents/paneSettings";

// Import view components
import connectDisplay from "./viewComponents/connectDisplay.vue";
import connectDisplayLite from "./viewComponents/connectDisplayLite.vue";
import streamDisplay from "./viewComponents/streamDisplay.vue";
import galleryDisplay from "./viewComponents/galleryDisplay.vue";

// Import plugin components
import JsonForm from "./pluginComponents/JsonForm";

// Export main app
export default {
  name: "PanelLeft",

  components: {
    tabIcon,
    tabContent,
    paneStatus,
    paneNavigate,
    paneCapture,
    paneSettings,
    JsonForm
  },

  data: function() {
    return {
      plugins: [],
      currentTab: "status",
      unwatchStoreFunction: null
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
          this.currentTab = "status";
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
}

#container-left {
  overflow: hidden auto;
  background-color: rgba(180, 180, 180, 0.025);
}

#container-left,
#switcher-left {
  border-width: 0 1px 0 0;
  border-style: solid;
  border-color: rgba(180, 180, 180, 0.25);
}

#switcher-left a {
  padding: 10px 8px;
}

#switcher-left {
  background-color: rgba(180, 180, 180, 0.1);
  padding-top: 2px !important;
}
</style>

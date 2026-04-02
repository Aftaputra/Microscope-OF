<template>
  <div id="app-content" class="uk-margin-remove uk-padding-remove uk-height-1-1" uk-grid>
    <!-- Initialisation modals -->
    <calibrationWizard ref="calibrationWizard" @on-close="enterApp()"></calibrationWizard>
    <!-- Vertical tab bar -->
    <div id="switcher-left-container">
      <div
        id="switcher-left"
        class="uk-flex uk-flex-column uk-padding-remove uk-width-auto uk-height-1-1 uk-text-center"
      >
        <!-- For each top tab -->
        <template v-for="(item, index) in topTabs" :key="item.id + '-tab-icon'">
          <!-- Render the tab icon -->
          <tabIcon
            :id="item.id + '-tab-icon'"
            :tab-i-d="item.id"
            :title="item.title"
            :require-connection="true"
            :current-tab="currentTab"
            :class="item.class"
            @set-tab="setTab"
          >
            <img
              v-if="item.iconURL"
              style="filter: grayscale(100%); width: 22px; margin-top: 5px; margin-bottom: 8px"
              :src="item.iconURL"
            />
            <span v-if="!item.iconURL" class="material-symbols-outlined">
              {{ item.icon }}
            </span>
          </tabIcon>
          <!-- Add a divider if item.divide is true -->
          <hr v-if="item.divide" :key="'tab-divider-' + index" />
        </template>

        <hr id="extension-tab-divider" />

        <!-- For each bottom tab -->
        <template v-for="(item, index) in bottomTabs" :key="item.id + '-tab-icon'">
          <!-- Render the tab icon -->
          <tabIcon
            :id="item.id + '-tab-icon'"
            :tab-i-d="item.id"
            :title="item.title"
            :require-connection="true"
            :current-tab="currentTab"
            :class="item.class"
            @set-tab="setTab"
          >
            <span class="material-symbols-outlined">{{ item.icon }}</span>
          </tabIcon>
          <!-- Add a divider if item.divide is true -->
          <hr v-if="item.divide" :key="'tab-divider-' + index" />
        </template>
      </div>
    </div>

    <!-- Corresponding vertical tab content -->
    <div
      id="container-left"
      ref="containerLeft"
      class="uk-padding-remove uk-height-1-1 uk-width-expand"
    >
      <tabContent
        v-for="item in allTabs"
        :id="item.id + '-tab-content'"
        :key="item.id + '-tab-content'"
        :tab-i-d="item.id"
        :require-connection="true"
        :current-tab="currentTab"
      >
        <component :is="item.component" @scroll-top="scrollToTop"></component>
      </tabContent>
    </div>
  </div>
</template>

<script>
// Import generic components
import tabIcon from "./genericComponents/tabIcon.vue";
import tabContent from "./genericComponents/tabContent.vue";

// Import new content components
import aboutContent from "./tabContentComponents/aboutContent.vue";
import controlContent from "./tabContentComponents/controlContent.vue";
import loggingContent from "./tabContentComponents/loggingContent.vue";
import powerContent from "./tabContentComponents/powerContent.vue";
import scanListContent from "./tabContentComponents/scanListContent.vue";
import settingsContent from "./tabContentComponents/settingsContent.vue";
import slideScanContent from "./tabContentComponents/slideScanContent.vue";
import viewContent from "./tabContentComponents/viewContent.vue";
import { markRaw } from "vue";
import { eventBus } from "../eventBus.js";

// Import modal components for device initialisation
import calibrationWizard from "./modalComponents/calibrationWizard.vue";

// Export main app
export default {
  name: "AppContent",

  components: {
    tabIcon,
    tabContent,
    calibrationWizard,
  },
  data: function () {
    return {
      currentTab: "view",
      bottomTabs: [
        {
          id: "settings",
          title: "Settings",
          icon: "settings",
          component: markRaw(settingsContent),
          class: "uk-margin-auto-top",
        },
        {
          id: "logging",
          title: "Logging",
          icon: "assignment_late",
          component: markRaw(loggingContent),
        },
        {
          id: "about",
          title: "About",
          icon: "info",
          component: markRaw(aboutContent),
        },
        {
          id: "power",
          title: "Power",
          icon: "power_settings_new",
          component: markRaw(powerContent),
        },
      ],
      coreTopTabs: [
        {
          id: "view",
          title: "View",
          icon: "visibility",
          component: markRaw(viewContent),
          requiredThings: [],
        },
        {
          id: "control",
          title: "Control",
          icon: "gamepad",
          component: markRaw(controlContent),
          requiredThings: [],
        },
        {
          id: "slide-scan",
          title: "Slide Scan",
          icon: "settings_overscan",
          component: markRaw(slideScanContent),
          requiredThings: ["smart_scan"],
        },
        {
          id: "scan-list",
          title: "Scan List",
          icon: "photo_library",
          component: markRaw(scanListContent),
          requiredThings: ["smart_scan"],
        },
      ],
    };
  },

  computed: {
    tabOrder: function () {
      var ind = [];
      for (const tab of this.topTabs) {
        ind.push(tab.id);
      }
      for (const tab of this.bottomTabs) {
        ind.push(tab.id);
      }
      return ind;
    },

    topTabs: function () {
      // Filter core top tabs based on available Things. Once Things can specify a
      // custom tab those will need to be added here
      return this.coreTopTabs.filter((tab) => {
        if (!tab.requiredThings || tab.requiredThings.length === 0) return true;
        return tab.requiredThings.every((thing) => this.thingAvailable(thing));
      });
    },
    allTabs() {
      return [...this.topTabs, ...this.bottomTabs];
    },
    currentTabIndex: function () {
      return this.tabOrder.indexOf(this.currentTab);
    },
  },

  mounted() {
    // A global signal listener to switch tab
    eventBus.on("globalSwitchTab", (tabID) => {
      this.currentTab = tabID;
    });
    // A global signal listener to increment tab
    eventBus.on("globalIncrementTab", () => {
      this.incrementTabBy(1);
    });
    // A global signal listener to decrement tab
    eventBus.on("globalDecrementTab", () => {
      this.incrementTabBy(-1);
    });
    if (this.$store.getters.ready) {
      this.startModals();
    }
  },

  methods: {
    setTab: function (event, tab) {
      if (!(this.currentTab == tab)) {
        this.currentTab = tab;
      }
    },
    incrementTabBy: function (n) {
      const newIndex =
        (((this.currentTabIndex + n) % this.tabOrder.length) + this.tabOrder.length) %
        this.tabOrder.length;
      const newId = this.tabOrder[newIndex];
      this.currentTab = newId;
    },
    startModals: function () {
      this.$refs.calibrationWizard.show_if_needed();
    },
    enterApp: function () {
      // Stuff to do once connected and all init modals are finished
    },
    scrollToTop() {
      this.$refs.containerLeft.scrollTo({ top: 0 });
    },
  },
};
</script>

<style scoped lang="less">
.window-container {
  width: 100%;
  height: 100%;
}
#component-left {
  width: 100%;
  height: 100%;
}

#container-left {
  overflow: auto;
  background-color: rgba(180, 180, 180, 0.025);
  width: 100%;
  height: 100%;
}

#switcher-left {
  width: 85px;
  padding-top: 2px !important;
}

#switcher-left-container {
  margin: 0;
  padding: 0;
  overflow-x: hidden;
  overflow-y: auto;
  height: 100%;
  background-color: rgba(180, 180, 180, 0.1);
  border-width: 0 1px 0 0;
  border-style: solid;
  border-color: rgba(180, 180, 180, 0.25);
}

#switcher-left a {
  padding: 10px 8px;
}
</style>

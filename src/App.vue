<template>
  <div
    id="app"
    class="uk-height-1-1 uk-margin-remove uk-padding-remove"
    :class="handleTheme"
  >
    <panelLeft />
  </div>
</template>

<script>
// Import components
import panelLeft from "./components/panelLeft.vue";

// Key Codes
const keyCodes = {
  pgup: 33,
  pgdn: 34,
  left: 37,
  up: 38,
  right: 39,
  down: 40,
  enter: 13,
  esc: 27,
  shift: 16
};

// Export main app
export default {
  name: "App",

  components: {
    panelLeft
  },

  data: function() {
    return {
      keysDown: {},
      systemDark: undefined,
      themeObserver: undefined
    };
  },

  computed: {
    isSystemDark: function() {
      if (
        window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: dark)").matches
      ) {
        return true;
      } else {
        return false;
      }
    },
    handleTheme: function() {
      var isDark = false;
      if (this.$store.state.globalSettings.appTheme == "dark") {
        isDark = true;
      } else if (this.$store.state.globalSettings.appTheme == "system") {
        if (this.systemDark) {
          isDark = true;
        }
      }
      return {
        "uk-light": isDark,
        "uk-background-secondary": isDark
      };
    }
  },

  mounted() {
    if (process.env.VUE_APP_LITEMODE == "true") {
      console.log("Built lite-mode");
    }
    // Query CSS dark theme preference
    var mql = window.matchMedia("(prefers-color-scheme: dark)");
    // Check for system dark theme when mounted
    if (mql.matches) {
      this.systemDark = true;
    }
    // Create a theme observer to watch for changes
    this.themeObserver = mql.addListener(e => {
      if (e.matches) {
        this.systemDark = true;
      } else {
        this.systemDark = false;
      }
    });
  },

  created: function() {
    window.addEventListener("beforeunload", this.handleExit);
    // Key events
    window.addEventListener("keydown", this.keyDownMonitor);
    window.addEventListener("keyup", this.keyUpMonitor);
    window.addEventListener("wheel", this.wheelMonitor);
  },

  beforeDestroy: function() {
    // Disconnect the theme observer
    if (this.themeObserver) {
      this.themeObserver.disconnect();
    }
    // Remove key listeners
    window.removeEventListener("keydown", this.keyDownMonitor);
    window.removeEventListener("keyup", this.keyUpMonitor);
    window.removeEventListener("wheel", this.wheelMonitor);
  },

  methods: {
    handleExit: function() {
      console.log("Triggered beforeunload");
      this.$root.$emit("globalTogglePreview", false);
    },

    // Handle global mouse wheel events to be associated with navigation
    wheelMonitor: function(event) {
      // Only capture scroll if the event target's parent contains the "scrollTarget" class
      if (
        event.target.parentNode.classList.contains("scrollTarget") ||
        event.target.classList.contains("scrollTarget")
      ) {
        var z_rel = event.deltaY / 100;
        // Emit a signal to move, acted on by panelNavigate.vue
        this.$root.$emit("globalMoveStepEvent", 0, 0, z_rel, false);
      }
    },

    // Handle global key press events to be associated with navigation
    keyDownMonitor: function(event) {
      this.keysDown[event.keyCode] = true; //Add key to array

      // Convert keyCode dict into a list of key codes
      var keyCodeList = Object.keys(keyCodes).map(function(key) {
        return keyCodes[key];
      });

      if (
        // If not inside an element we want to ignore
        !(event.target instanceof HTMLInputElement) &&
        !event.target.classList.contains("lightbox-link") &&
        // If it's a recognised key
        keyCodeList.includes(event.keyCode)
      ) {
        this.navigateKeyHandler(keyCodes);
        this.captureKeyHandler(keyCodes);
      }
    },

    keyUpMonitor: function(event) {
      delete this.keysDown[event.keyCode]; //Remove key from array
    },

    navigateKeyHandler: function(keyCodes) {
      const moveKeys = [
        keyCodes.left,
        keyCodes.right,
        keyCodes.up,
        keyCodes.down,
        keyCodes.pgup,
        keyCodes.pgdn
      ];

      if (
        moveKeys.some(r => Object.keys(this.keysDown).includes(r.toString()))
      ) {
        // Calculate movement array
        var x_rel = 0;
        var y_rel = 0;
        var z_rel = 0;
        if (keyCodes.left in this.keysDown) {
          x_rel = x_rel + 1;
        }
        if (keyCodes.right in this.keysDown) {
          x_rel = x_rel - 1;
        }
        if (keyCodes.up in this.keysDown) {
          y_rel = y_rel + 1;
        }
        if (keyCodes.down in this.keysDown) {
          y_rel = y_rel - 1;
        }
        if (keyCodes.pgup in this.keysDown) {
          z_rel = z_rel - 1;
        }
        if (keyCodes.pgdn in this.keysDown) {
          z_rel = z_rel + 1;
        }
        // Make a position request
        // Emit a signal to move, acted on by panelNavigate.vue
        this.$root.$emit("globalMoveStepEvent", x_rel, y_rel, z_rel);
      }
    },

    captureKeyHandler: function(keyCodes) {
      if (keyCodes.shift in this.keysDown && keyCodes.enter in this.keysDown) {
        console.log("Capturing");
        this.$root.$emit("globalCaptureEvent");
      }
    }
  }
};
</script>

<style lang="less">
// Basic UIkit CSS
@import "../node_modules/uikit/src/less/uikit.less";
// Custom UIkit CSS modifications
@import "./assets/less/theme.less";

// We override the custom-electron-titlebar z-index
// UIKit lightbox must be able to draw over the titlebar
// as it currently always spawns at the root of the DOM
.titlebar,
.titlebar > * {
  z-index: 1000 !important;
}

#app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: left;
  height: 100%;
}

body,
html {
  height: 100%;
  overflow: hidden;
}

.uk-disabled {
  pointer-events: none;
  opacity: 0.4;
}

.control-component {
  overflow-y: auto;
  overflow-x: hidden;
  width: 300px;
  height: 100%;
  padding: 0;
  background-color: rgba(180, 180, 180, 0.03);
  border-width: 0 1px 0 0;
  border-style: solid;
  border-color: rgba(180, 180, 180, 0.25);
}

.view-component {
  overflow-y: auto;
  overflow-x: hidden;
  height: 100%;
  padding: 0;
}
</style>

import { defineStore } from "pinia";
import { ref, computed } from "vue";

function getOriginFromLocation() {
  // This will default to the same origin that's serving
  // the web app.
  let url = new URL(window.location.href);
  return `${url.origin}/api/v3`;
}

// Define Pinia store
export const useSettingsStore = defineStore(
  "settings",
  () => {
    // State
    const origin = ref(getOriginFromLocation());
    const available = ref(false);
    const waiting = ref(false);
    const error = ref("");
    const trackWindow = ref(true);
    const activeStreams = ref({});
    const microscopeHostname = ref("");

    // Persistent items:
    // The app theme (e.g. light/dark)
    const appTheme = ref("system");
    const disableStream = ref(false);
    // The origin to use if overriding with dev tools
    const overrideOrigin = ref("http://microscope.local:5000/api/v3");
    // The step sizes for navigation via control pane/keys presses
    const navigationStepSize = ref({
      x: 200,
      y: 200,
      z: 50,
    });
    // The axis inversion for navigation via control pane/keys presses
    const navigationInvert = ref({
      x: false,
      y: false,
      z: false,
    });

    // Actions
    function resetState() {
      waiting.value = false;
      available.value = false;
      // On resetState there is no connection.
      error.value = "Microscope is not connected.";
    }

    function setConnected() {
      waiting.value = false;
      available.value = true;
    }

    function addStream(id) {
      activeStreams.value[id] = true;
    }
    function removeStream(id) {
      activeStreams.value[id] = false;
    }
    // Getters
    const baseUri = computed(() => origin.value);
    const ready = computed(() => available.value);

    // Export
    return {
      //State
      origin,
      available,
      waiting,
      error,
      trackWindow,
      activeStreams,
      microscopeHostname,
      appTheme,
      disableStream,
      overrideOrigin,
      navigationStepSize,
      navigationInvert,

      //Getters
      baseUri,
      ready,

      //Actions
      resetState,
      setConnected,
      addStream,
      removeStream,
    };
  },
  {
    // PiniaPluginPersistedState will now automatically persist ONLY these specific refs to localStorage
    persist: {
      pick: [
        "appTheme",
        "overrideOrigin",
        "disableStream",
        "navigationStepSize",
        "navigationInvert",
      ],
    },
  },
);

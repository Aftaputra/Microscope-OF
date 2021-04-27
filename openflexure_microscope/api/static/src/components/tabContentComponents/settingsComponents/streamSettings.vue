<template>
  <div id="streamSettings" class="uk-width-large">
    <div>
      <h3>Stream settings</h3>
      <label
        ><input v-model="disableStream" class="uk-checkbox" type="checkbox" />
        Disable web stream</label
      >
      <p class="uk-margin-small">
        This will disable the embedded web stream of the camera.
      </p>
    </div>

    <br />

    <div>
      <h3>Microscope display output</h3>
      <div uk-grid>
        <div>
          <label :class="[{ 'uk-disabled': !this.$store.getters.ready }]"
            ><input
              v-model="autoGpuPreview"
              class="uk-checkbox"
              type="checkbox"
            />
            Enable GPU preview</label
          >
        </div>
        <div>
          <label :class="[{ 'uk-disabled': !this.$store.getters.ready }]"
            ><input v-model="trackWindow" class="uk-checkbox" type="checkbox" />
            Track window</label
          >
        </div>
      </div>
      <p>
        Enable GPU preview turns on a low-latency camera preview drawn directly
        to the Raspberry Pi display output.
      </p>
      <p class="uk-margin-small">
        <b
          >Content, such as your mouse, won't be visible behind this preview.</b
        >
        Track Window will attempt to resize the GPU preview based on the current
        window size, however this is often imperfect and cannot track window
        movement.
      </p>
    </div>
  </div>
</template>

<script>
// Export main app
export default {
  name: "StreamSettings",

  data: function() {
    return {};
  },

  computed: {
    disableStream: {
      get() {
        return this.$store.state.disableStream;
      },
      set(value) {
        this.$store.commit("changeDisableStream", value);
      }
    },

    autoGpuPreview: {
      get() {
        return this.$store.state.autoGpuPreview;
      },
      set(value) {
        // NB the stream viewer watches the store, and is
        // responsible for making the request that switches
        // GPU preview on/off
        // see streamContent.vue
        this.$store.commit("changeAutoGpuPreview", value);
      }
    },

    trackWindow: {
      get() {
        return this.$store.state.trackWindow;
      },
      set(value) {
        this.$store.commit("changeTrackWindow", value);
      }
    }
  },

  watch: {
    // Cache the stream settings to local storage for persistence
    // (the next 3 functions all relate to this)
    disableStream: function(newValue) {
      console.log(`disableStream updated to ${newValue} and saved in local storage`);
    },
    autoGpuPreview: function(newValue) {
      console.log(`GPU preview updated to ${newValue} and saved in local storage`);
    },
    trackWindow: function(newValue) {
      console.log(`trackWindow updated to ${newValue} and saved in local storage`);
    }
  },

  created() {
    // Apply sensible defaults for stream settings, depending on
    // whether we're connecting locally or remotely, respecting
    // the settings that were cached previously.
    const localMode = ["localhost", "0.0.0.0", "127.0.0.1", "[::1]"].includes(
      window.location.hostname
    );
    const localDefaults = {
      disableStream: true,
      autoGpuPreview: true,
      trackWindow: true
    };
    for (let k in localDefaults) {
      if (localStorage.getItem(k) !== null) {
        this[k] = this.getLocalStorageObj(k);
      } else if (localMode) {
        console.log(`${k} set to default value for a local connection`);
        this[k] = localDefaults[k];
      }
    }
  }
};
</script>

<style lang="less"></style>

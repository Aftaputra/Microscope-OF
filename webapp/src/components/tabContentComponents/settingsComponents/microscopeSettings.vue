<template>
  <div v-if="settings" id="microscopeSettings" class="uk-width-large">
    <form @submit.prevent="applySettingsRequest">
      <div>
        <label class="uk-form-label" for="form-stacked-text"
          >Microscope name</label
        >
        <input
          v-model="settings.name"
          class="uk-input uk-width-1-1 uk-form-small"
          name="inputFilename"
          placeholder="Leave blank for default"
        />
      </div>

      <br />

      <button
        type="submit"
        class="uk-button uk-button-primary uk-margin-small uk-width-1-1"
      >
        Apply Settings
      </button>
    </form>
  </div>
</template>

<script>
import axios from "axios";

// Export main app
export default {
  name: "MicroscopeSettings",

  data: function() {
    return {
      settings: null
    };
  },

  computed: {
    settingsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/instrument/settings`;
    }
  },

  mounted() {
    this.updateSettings();
  },

  methods: {
    updateSettings: function() {
      axios
        .get(this.settingsUri)
        .then(response => {
          this.settings = response.data;
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    applySettingsRequest: function() {
      var payload = {
        name: this.settings.name
      };

      // Send request to update config
      axios
        .put(this.settingsUri, payload)
        .then(() => {
          // Update local settings
          this.updateSettings();
          this.modalNotify("Microscope settings applied.");
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    }
  }
};
</script>

<style lang="less">
.center-spinner {
  margin-left: auto;
  margin-right: auto;
}
</style>
